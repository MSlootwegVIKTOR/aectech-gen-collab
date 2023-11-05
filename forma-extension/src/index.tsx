import { render } from "preact";
import "./style.css";
import { useCallback, useEffect, useState } from "preact/hooks";
import { Forma } from "forma-embedded-view-sdk/auto";

import { GLTFExporter } from "three/addons/exporters/GLTFExporter.js";
import * as THREE from "three";

export function App() {
  const [positions, setPositions] = useState<Float32Array | null>(null);

  useEffect(() => {
    Forma.geometry.getTriangles({ path: "root" }).then((triangles) => {
      setPositions(triangles);
    });
  }, []);

  const glbExportToStorage = useCallback(async () => {
    if (!positions) return;
    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute("position", new THREE.BufferAttribute(positions, 3));

    const edges = new THREE.EdgesGeometry(geometry);
    const line = new THREE.LineSegments(
      edges,
      new THREE.LineBasicMaterial({ color: 0xffffff })
    );

    const material = new THREE.MeshBasicMaterial({ color: 0x000000 });
    const mesh = new THREE.Mesh(geometry, material);
    const exporter = new GLTFExporter();

    const scene = new THREE.Scene();
    scene.add(line);
    scene.add(mesh);

    exporter.parse(
      scene,
      async (gltf) => {
        const json = JSON.stringify(gltf);
        Forma.extensions.storage.setObject({ key: "export.gltf", data: json });
      },
      undefined,
      { binary: false }
    );
  }, [positions]);
  return (
    <div>
      {positions && <div>{positions.length / 9} triangles</div>}
      {positions && (
        <button onClick={glbExportToStorage}>Store to extension storage</button>
      )}
    </div>
  );
}

render(<App />, document.getElementById("app"));
