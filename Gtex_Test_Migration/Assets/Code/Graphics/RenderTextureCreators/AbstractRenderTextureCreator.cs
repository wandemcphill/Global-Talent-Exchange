
using FStudio.Utilities;
using UnityEngine;

namespace FStudio.Graphics.RenderTextureCreators {
    public abstract class AbstractRenderTextureCreator<T> : SceneObjectSingleton<T> where T : Object {
#pragma warning disable 0109
        [SerializeField] private new Camera camera;
#pragma warning restore 0109
        [SerializeField] private int resolution = 256;

        protected RenderTexture Render () {
            var renderTextureDescription = new RenderTextureDescriptor(resolution, resolution, RenderTextureFormat.ARGB32);
            
            var renderTexture = new RenderTexture(renderTextureDescription);
            renderTexture.wrapMode = TextureWrapMode.Repeat;
            
            camera.targetTexture = renderTexture;
            camera.Render();

            return renderTexture;
        }
    }
}
