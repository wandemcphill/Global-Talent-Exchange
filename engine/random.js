function createRNG(seed) {
  let state = Number(seed) >>> 0;
  if (state === 0) {
    state = 0x6d2b79f5;
  }

  function nextFloat() {
    state += 0x6d2b79f5;
    let value = state;
    value = Math.imul(value ^ (value >>> 15), value | 1);
    value ^= value + Math.imul(value ^ (value >>> 7), value | 61);
    return ((value ^ (value >>> 14)) >>> 0) / 4294967296;
  }

  return {
    nextFloat,
    nextInt(min, max) {
      const low = Math.ceil(Math.min(min, max));
      const high = Math.floor(Math.max(min, max));
      return low + Math.floor(nextFloat() * (high - low + 1));
    },
    chance(probability) {
      return nextFloat() <= Math.max(0, Math.min(1, probability));
    },
    pick(items) {
      if (!Array.isArray(items) || items.length === 0) {
        return null;
      }

      return items[this.nextInt(0, items.length - 1)];
    },
  };
}

module.exports = { createRNG };
