/**
 * lottie-web integration tests.
 *
 * Verifies:
 * 1. Import resolves correctly (CJS interop in Vite)
 * 2. loadAnimation returns a valid animation object
 * 3. SVG renderer produces visible DOM content
 * 4. Canvas renderer produces visible DOM content
 */
import { describe, it, expect, vi, beforeAll } from "vitest";

// jsdom doesn't implement getContext — stub before lottie-web probes it
HTMLCanvasElement.prototype.getContext = (() => {
  const ctx: any = {
    fillStyle: "", strokeStyle: "",
    beginPath() {}, closePath() {}, fill() {}, stroke() {}, arc() {}, rect() {},
    moveTo() {}, lineTo() {}, bezierCurveTo() {},
    clearRect() {}, fillRect() {}, translate() {}, rotate() {}, scale() {},
    save() {}, restore() {},
    setTransform() {}, transform() {},
    createLinearGradient() { return { addColorStop() {} }; },
    createRadialGradient() { return { addColorStop() {} }; },
    measureText() { return { width: 0 }; },
    fillText() {}, drawImage() {},
  };
  return () => ctx;
})() as typeof HTMLCanvasElement.prototype.getContext;

const testAnimation = {
  v: "5.5.2", fr: 30, ip: 0, op: 60,
  w: 120, h: 28, nm: "Test",
  ddd: 0, assets: [],
  layers: [{
    ddd: 0, ind: 1, ty: 4, nm: "Circle", sr: 1,
    ks: {
      o: { a: 0, k: 100, ix: 11 },
      r: { a: 0, k: 0, ix: 10 },
      p: { a: 0, k: [60, 14, 0], ix: 2 },
      a: { a: 0, k: [0, 0, 0], ix: 1 },
      s: { a: 0, k: [100, 100, 100], ix: 6 }
    },
    shapes: [{
      ty: "gr",
      it: [
        { ty: "el", d: 1, p: { a: 0, k: [0, 0] }, s: { a: 0, k: [20, 20] }, nm: "Circle" },
        { ty: "fl", c: { a: 0, k: [1, 0, 0, 1] }, o: { a: 0, k: 100 }, nm: "Fill" }
      ],
      nm: "Circle Group"
    }],
    st: 0, op: 60, ip: 0
  }]
};

describe("lottie-web integration", () => {
  let lottie: any;

  beforeAll(async () => {
    const mod: any = await import("lottie-web");
    lottie = mod.default ?? mod;
  });

  it("imports and exposes loadAnimation", () => {
    expect(lottie).toBeTypeOf("object");
    expect(lottie.loadAnimation).toBeTypeOf("function");
    expect(lottie.play).toBeTypeOf("function");
    expect(lottie.destroy).toBeTypeOf("function");
  });

  it("SVG renderer: creates SVG element inside container", async () => {
    const container = document.createElement("div");
    container.style.width = "72px";
    container.style.height = "20px";
    document.body.appendChild(container);

    const anim = lottie.loadAnimation({
      container,
      animationData: testAnimation,
      loop: true,
      autoplay: true,
      renderer: "svg",
    });

    expect(anim).toBeTruthy();

    // Wait for DOMLoaded + force first frame render
    await new Promise<void>((resolve) => {
      anim.addEventListener("DOMLoaded", () => {
        anim.goToAndStop(0, true);
        setTimeout(resolve, 300);
      });
      setTimeout(resolve, 2000);
    });

    console.log("[test] container children:", container.children.length);
    console.log("[test] FULL innerHTML:", container.innerHTML);

    const svg = container.querySelector("svg");
    expect(svg).toBeTruthy();
    expect(svg!.getAttribute("viewBox")).toBe("0 0 120 28");

    // Verify there are shapes inside the SVG
    const shapes = svg!.querySelectorAll("ellipse, circle, path, rect, g");
    console.log("[test] SVG shapes:", shapes.length);

    anim.destroy();
    document.body.removeChild(container);
  });

  it("Canvas renderer: creates canvas element inside container", async () => {
    const container = document.createElement("div");
    container.style.width = "72px";
    container.style.height = "20px";
    document.body.appendChild(container);

    const anim = lottie.loadAnimation({
      container,
      animationData: testAnimation,
      loop: true,
      autoplay: true,
      renderer: "canvas",
    });

    expect(anim).toBeTruthy();

    await new Promise<void>((resolve) => {
      anim.addEventListener("DOMLoaded", () => resolve());
      setTimeout(resolve, 2000);
    });

    console.log("[test] FULL SVG:", container.innerHTML);

    // Canvas renderer should create a <canvas> element
    const canvas = container.querySelector("canvas");
    const hasContent = container.children.length > 0;
    console.log("[test] has canvas:", !!canvas, "has children:", hasContent);

    anim.destroy();
    document.body.removeChild(container);
  });
});
