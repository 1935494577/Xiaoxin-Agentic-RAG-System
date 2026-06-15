import { useEffect, useRef } from "react";

type ThreeNamespace = {
  Camera: new () => THREECamera;
  Scene: new () => THREEObject;
  PlaneBufferGeometry: new (w: number, h: number) => THREEBufferGeometry;
  Vector2: new (x?: number, y?: number) => THREEVector2;
  ShaderMaterial: new (params: ShaderMaterialParams) => THREEMaterial;
  Mesh: new (geometry: THREEBufferGeometry, material: THREEMaterial) => THREEObject;
  WebGLRenderer: new () => THREEWebGLRenderer;
};

type THREECamera = { position: { z: number } };
type THREEObject = { add: (child: THREEObject) => void };
type THREEBufferGeometry = object;
type THREEMaterial = object;
type THREEVector2 = { x: number; y: number };
type ShaderMaterialParams = {
  uniforms: Record<string, { type: string; value: number | THREEVector2 }>;
  vertexShader: string;
  fragmentShader: string;
};
type THREEWebGLRenderer = {
  domElement: HTMLCanvasElement;
  setPixelRatio: (ratio: number) => void;
  setSize: (w: number, h: number) => void;
  render: (scene: THREEObject, camera: THREECamera) => void;
  dispose: () => void;
};

declare global {
  interface Window {
    THREE?: ThreeNamespace;
  }
}

const THREE_CDN =
  "https://cdnjs.cloudflare.com/ajax/libs/three.js/89/three.min.js";

export function ShaderAnimation() {
  const containerRef = useRef<HTMLDivElement>(null);
  const sceneRef = useRef<{
    camera: THREECamera | null;
    scene: THREEObject | null;
    renderer: THREEWebGLRenderer | null;
    uniforms: Record<string, { type: string; value: number | THREEVector2 }> | null;
    animationId: number | null;
    resizeHandler: (() => void) | null;
    scriptEl: HTMLScriptElement | null;
  }>({
    camera: null,
    scene: null,
    renderer: null,
    uniforms: null,
    animationId: null,
    resizeHandler: null,
    scriptEl: null,
  });

  useEffect(() => {
    let cancelled = false;

    const initThreeJS = () => {
      if (cancelled || !containerRef.current || !window.THREE) return;

      const THREE = window.THREE;
      const container = containerRef.current;
      container.innerHTML = "";

      const camera = new THREE.Camera();
      camera.position.z = 1;

      const scene = new THREE.Scene();
      const geometry = new THREE.PlaneBufferGeometry(2, 2);

      const uniforms = {
        time: { type: "f", value: 1.0 },
        resolution: { type: "v2", value: new THREE.Vector2() },
      };

      const vertexShader = `
        void main() {
          gl_Position = vec4( position, 1.0 );
        }
      `;

      const fragmentShader = `
        #define TWO_PI 6.2831853072
        #define PI 3.14159265359

        precision highp float;
        uniform vec2 resolution;
        uniform float time;

        float random (in float x) {
          return fract(sin(x)*1e4);
        }
        float random (vec2 st) {
          return fract(sin(dot(st.xy, vec2(12.9898,78.233))) * 43758.5453123);
        }

        void main(void) {
          vec2 uv = (gl_FragCoord.xy * 2.0 - resolution.xy) / min(resolution.x, resolution.y);

          vec2 fMosaicScal = vec2(4.0, 2.0);
          vec2 vScreenSize = vec2(256,256);
          uv.x = floor(uv.x * vScreenSize.x / fMosaicScal.x) / (vScreenSize.x / fMosaicScal.x);
          uv.y = floor(uv.y * vScreenSize.y / fMosaicScal.y) / (vScreenSize.y / fMosaicScal.y);

          float t = time*0.06+random(uv.x)*0.4;
          float lineWidth = 0.0008;

          vec3 color = vec3(0.0);
          for(int j = 0; j < 3; j++){
            for(int i=0; i < 5; i++){
              color[j] += lineWidth*float(i*i) / abs(fract(t - 0.01*float(j)+float(i)*0.01)*1.0 - length(uv));
            }
          }

          gl_FragColor = vec4(color[2],color[1],color[0],1.0);
        }
      `;

      const material = new THREE.ShaderMaterial({
        uniforms,
        vertexShader,
        fragmentShader,
      });

      const mesh = new THREE.Mesh(geometry, material);
      scene.add(mesh);

      const renderer = new THREE.WebGLRenderer();
      renderer.setPixelRatio(window.devicePixelRatio);
      container.appendChild(renderer.domElement);

      sceneRef.current.camera = camera;
      sceneRef.current.scene = scene;
      sceneRef.current.renderer = renderer;
      sceneRef.current.uniforms = uniforms;

      const onWindowResize = () => {
        const rect = container.getBoundingClientRect();
        renderer.setSize(rect.width, rect.height);
        const res = uniforms.resolution.value as THREEVector2;
        res.x = renderer.domElement.width;
        res.y = renderer.domElement.height;
      };

      onWindowResize();
      window.addEventListener("resize", onWindowResize, false);
      sceneRef.current.resizeHandler = onWindowResize;

      const animate = () => {
        sceneRef.current.animationId = requestAnimationFrame(animate);
        (uniforms.time.value as number) += 0.05;
        renderer.render(scene, camera);
      };

      animate();
    };

    const boot = () => {
      if (window.THREE) {
        initThreeJS();
        return;
      }
      const script = document.createElement("script");
      script.src = THREE_CDN;
      script.async = true;
      script.onload = () => initThreeJS();
      document.head.appendChild(script);
      sceneRef.current.scriptEl = script;
    };

    boot();

    return () => {
      cancelled = true;
      const s = sceneRef.current;
      if (s.animationId) cancelAnimationFrame(s.animationId);
      if (s.resizeHandler) window.removeEventListener("resize", s.resizeHandler, false);
      if (s.renderer) s.renderer.dispose();
      if (s.scriptEl?.parentNode) s.scriptEl.parentNode.removeChild(s.scriptEl);
      s.camera = null;
      s.scene = null;
      s.renderer = null;
      s.uniforms = null;
      s.animationId = null;
      s.resizeHandler = null;
      s.scriptEl = null;
    };
  }, []);

  return <div ref={containerRef} className="absolute inset-0 h-full w-full" />;
}
