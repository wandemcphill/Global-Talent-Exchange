/** Jest stand-in. The real helper is an ES module Jest does not transform. */
function clone(source) {
  if (source && typeof source.clone === "function") return source.clone(true);
  return source;
}

module.exports = { clone };
