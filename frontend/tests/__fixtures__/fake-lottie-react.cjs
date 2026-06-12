"use strict";
Object.defineProperty(exports, "__esModule", { value: true });

// Simulates lottie-react's CJS export pattern:
//   exports["default"] = LottieComponent;
//   exports.useLottie = ...;
//   exports.useLottieInteractivity = ...;

function FakeLottieComponent() {
  return null;
}

function fakeUseLottie() {
  return { View: null, play: function () {}, stop: function () {}, destroy: function () {} };
}

function fakeUseLottieInteractivity() {}

exports["default"] = FakeLottieComponent;
exports.useLottie = fakeUseLottie;
exports.useLottieInteractivity = fakeUseLottieInteractivity;
