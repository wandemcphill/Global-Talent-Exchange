/**
 * GTEX Living Football Ecosystem — WebGL 3D Match Broadcast
 * Progressive 3D Asset Streaming & IndexedDB Persistent Cache (Track 3 Upgrade).
 *
 * Implements:
 * 1. Two-tier caching: In-memory ArrayBuffer cache + Persistent IndexedDB blob store.
 * 2. glTF decoding via lazily imported GLTFLoader + DRACOLoader + KTX2Loader + Meshopt.
 *    Decoder binaries are served from `/decoders/draco/` and `/decoders/basis/` by default
 *    (copy them from three/examples/jsm/libs/{draco,basis}); override with setDecoderPaths.
 * 3. Zero-wait model instantiation on subsequent matches for returning spectators.
 * 4. Failed fetches are never cached (prevents poisoning the persistent store).
 */

export interface AssetStreamingSummary {
  cachedAssetCount: number;
  memoryCacheHits: number;
  indexedDbCacheHits: number;
  networkFetches: number;
  isIndexedDbSupported: boolean;
  totalBytesCached: number;
  gltfDecodes: number;
}

export interface DecoderPaths {
  dracoDecoderPath: string;
  basisTranscoderPath: string;
}

/** Minimal shape of a decoded glTF (mirrors three's GLTF without importing jsm types). */
export interface GltfLoadResult {
  scene: any;
  animations: any[];
  [key: string]: any;
}

export type GltfParser = (buffer: ArrayBuffer, resourcePath: string) => Promise<GltfLoadResult>;
export type GltfLoaderFactory = (paths: DecoderPaths, renderer?: unknown) => Promise<GltfParser>;

const defaultGltfLoaderFactory: GltfLoaderFactory = async (paths, renderer) => {
  const [{ GLTFLoader }, { DRACOLoader }, { KTX2Loader }, { MeshoptDecoder }] = await Promise.all([
    import(/* webpackChunkName: "gltf-loader" */ "three/examples/jsm/loaders/GLTFLoader.js"),
    import(/* webpackChunkName: "gltf-loader" */ "three/examples/jsm/loaders/DRACOLoader.js"),
    import(/* webpackChunkName: "gltf-loader" */ "three/examples/jsm/loaders/KTX2Loader.js"),
    import(/* webpackChunkName: "gltf-loader" */ "three/examples/jsm/libs/meshopt_decoder.module.js"),
  ]);
  const loader = new GLTFLoader();
  const draco = new DRACOLoader();
  draco.setDecoderPath(paths.dracoDecoderPath);
  loader.setDRACOLoader(draco);
  const ktx2 = new KTX2Loader();
  ktx2.setTranscoderPath(paths.basisTranscoderPath);
  if (renderer) {
    // detectSupport picks ASTC/BC7/ETC2/S3TC targets for the actual GPU
    ktx2.detectSupport(renderer as import("three").WebGLRenderer);
  }
  loader.setKTX2Loader(ktx2);
  loader.setMeshoptDecoder(MeshoptDecoder);
  return (buffer, resourcePath) =>
    new Promise<GltfLoadResult>((resolve, reject) => {
      loader.parse(buffer, resourcePath, (gltf) => resolve(gltf as unknown as GltfLoadResult), reject);
    });
};

const DB_NAME = "GTEX_3D_ASSET_CACHE";
const DB_VERSION = 1;
const STORE_NAME = "assets";

export class AssetStreamingCache {
  private static instance: AssetStreamingCache | null = null;
  private memoryCache = new Map<string, ArrayBuffer>();
  private memoryCacheHits = 0;
  private indexedDbCacheHits = 0;
  private networkFetches = 0;
  private totalBytesCached = 0;
  private dbPromise: Promise<IDBDatabase | null> | null = null;
  private gltfDecodes = 0;
  private gltfLoaderFactory: GltfLoaderFactory | null = null;
  private gltfLoaderPromise: Promise<GltfParser> | null = null;
  private decoderPaths: DecoderPaths = {
    dracoDecoderPath: "/decoders/draco/",
    basisTranscoderPath: "/decoders/basis/",
  };

  public static getInstance(): AssetStreamingCache {
    if (!AssetStreamingCache.instance) {
      AssetStreamingCache.instance = new AssetStreamingCache();
    }
    return AssetStreamingCache.instance;
  }

  constructor() {
    this.dbPromise = this.openDatabase();
  }

  private isIndexedDbAvailable(): boolean {
    return (
      typeof window !== "undefined" &&
      typeof window.indexedDB !== "undefined" &&
      typeof window.indexedDB.open === "function"
    );
  }

  private async openDatabase(): Promise<IDBDatabase | null> {
    if (!this.isIndexedDbAvailable()) return null;

    return new Promise((resolve) => {
      try {
        const req = window.indexedDB.open(DB_NAME, DB_VERSION);
        req.onupgradeneeded = (e) => {
          const db = (e.target as IDBOpenDBRequest).result;
          if (!db.objectStoreNames.contains(STORE_NAME)) {
            db.createObjectStore(STORE_NAME);
          }
        };
        req.onsuccess = () => resolve(req.result);
        req.onerror = () => resolve(null);
      } catch {
        resolve(null);
      }
    });
  }

  /**
   * Loads an ArrayBuffer from memory cache, IndexedDB, or network fetch.
   */
  public async loadAsset(
    url: string,
    onProgress?: (progressPct: number) => void
  ): Promise<ArrayBuffer> {
    // 1. Check in-memory cache
    if (this.memoryCache.has(url)) {
      this.memoryCacheHits++;
      onProgress?.(100);
      return this.memoryCache.get(url)!;
    }

    // 2. Check persistent IndexedDB cache
    const db = await this.dbPromise;
    if (db) {
      const fromDb = await this.readFromDb(db, url);
      if (fromDb) {
        this.indexedDbCacheHits++;
        this.memoryCache.set(url, fromDb);
        onProgress?.(100);
        return fromDb;
      }
    }

    // 3. Network fetch. Failures are thrown and never cached, so a bad response
    //    can't poison the persistent IndexedDB store for future sessions.
    if (typeof fetch !== "function") {
      throw new Error(`fetch unavailable; cannot load 3D asset ${url}`);
    }
    this.networkFetches++;
    const res = await fetch(url);
    if (!res || !res.ok) {
      throw new Error(`Failed to fetch 3D asset from ${url}: HTTP ${res ? res.status : "n/a"}`);
    }
    const buffer = await res.arrayBuffer();
    this.memoryCache.set(url, buffer);
    this.totalBytesCached += buffer.byteLength;
    if (db) {
      this.writeToDb(db, url, buffer).catch(() => {});
    }
    onProgress?.(100);
    return buffer;
  }

  // ---------------------------------------------------------------------------
  // glTF / GLB decoding with Draco, KTX2 (Basis Universal) and Meshopt support
  // ---------------------------------------------------------------------------

  /**
   * Overrides how the glTF loader stack is created. Production uses lazily imported
   * three/examples loaders; tests inject a fake so no ESM is pulled into Jest.
   */
  public setGltfLoaderFactory(factory: GltfLoaderFactory | null): void {
    this.gltfLoaderFactory = factory;
    this.gltfLoaderPromise = null;
  }

  public setDecoderPaths(paths: Partial<DecoderPaths>): void {
    this.decoderPaths = { ...this.decoderPaths, ...paths };
    this.gltfLoaderPromise = null;
  }

  private getGltfParser(renderer?: unknown): Promise<GltfParser> {
    if (!this.gltfLoaderPromise) {
      const factory = this.gltfLoaderFactory ?? defaultGltfLoaderFactory;
      this.gltfLoaderPromise = factory(this.decoderPaths, renderer);
    }
    return this.gltfLoaderPromise;
  }

  /**
   * Fetches (through the two-tier cache) and decodes a glTF binary. Draco-compressed
   * geometry, KTX2 textures and Meshopt buffers are decoded by the configured loader stack.
   */
  public async loadGLTF(url: string, renderer?: unknown): Promise<GltfLoadResult> {
    const buffer = await this.loadAsset(url);
    const parser = await this.getGltfParser(renderer);
    const resourcePath = url.substring(0, url.lastIndexOf("/") + 1);
    this.gltfDecodes++;
    return parser(buffer, resourcePath);
  }

  public async loadGltf(url: string, renderer?: unknown): Promise<GltfLoadResult> {
    return this.loadGLTF(url, renderer);
  }


  private readFromDb(db: IDBDatabase, key: string): Promise<ArrayBuffer | null> {
    return new Promise((resolve) => {
      try {
        const tx = db.transaction(STORE_NAME, "readonly");
        const store = tx.objectStore(STORE_NAME);
        const req = store.get(key);
        req.onsuccess = () => resolve(req.result ? (req.result as ArrayBuffer) : null);
        req.onerror = () => resolve(null);
      } catch {
        resolve(null);
      }
    });
  }

  private writeToDb(db: IDBDatabase, key: string, data: ArrayBuffer): Promise<void> {
    return new Promise((resolve) => {
      try {
        const tx = db.transaction(STORE_NAME, "readwrite");
        const store = tx.objectStore(STORE_NAME);
        store.put(data, key);
        tx.oncomplete = () => resolve();
        tx.onerror = () => resolve();
      } catch {
        resolve();
      }
    });
  }

  public has(url: string): boolean {
    return this.memoryCache.has(url);
  }

  public async clearCache(): Promise<void> {
    this.memoryCache.clear();
    this.totalBytesCached = 0;
    const db = await this.dbPromise;
    if (db) {
      try {
        const tx = db.transaction(STORE_NAME, "readwrite");
        tx.objectStore(STORE_NAME).clear();
      } catch {
        // Ignore
      }
    }
  }

  public getSummary(): AssetStreamingSummary {
    return {
      cachedAssetCount: this.memoryCache.size,
      memoryCacheHits: this.memoryCacheHits,
      indexedDbCacheHits: this.indexedDbCacheHits,
      networkFetches: this.networkFetches,
      isIndexedDbSupported: this.isIndexedDbAvailable(),
      totalBytesCached: this.totalBytesCached,
      gltfDecodes: this.gltfDecodes,
    };
  }
}
