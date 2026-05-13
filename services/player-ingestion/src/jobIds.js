"use strict";

function safeJobId(...parts) {
  return parts.map((part) => String(part ?? "none").replace(/[^A-Za-z0-9_-]/g, "_")).join("-");
}

module.exports = {
  safeJobId,
};
