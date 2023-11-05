import { render } from "preact";
import "./style.css";
import { useCallback, useEffect, useState } from "preact/hooks";
import { Forma } from "forma-embedded-view-sdk/auto";

import { GLTFExporter } from "three/addons/exporters/GLTFExporter.js";
import * as THREE from "three";

export function App() {
  const [terrainPositions, setTerrainPositions] = useState<Float32Array | null>(
    null
  );
  const [perBuildingPositions, setPerBuildingPositions] = useState<
    Float32Array[]
  >([]);

  useEffect(() => {
    Forma.geometry.getPathsByCategory({ category: "terrain" }).then((paths) => {
      Forma.geometry.getTriangles({ path: paths[0] }).then((triangles) => {
        setTerrainPositions(triangles);
      });
    });
    Forma.geometry
      .getPathsByCategory({ category: "building" })
      .then((paths) => {
        console.log(paths.length);
        const promises = paths.map((path) => {
          return Forma.geometry.getTriangles({ path });
        });
        Promise.all(promises).then((per_building_positions) => {
          setPerBuildingPositions(per_building_positions);
        });
      });
  }, []);

  const terrainGlbExportToStorage = useCallback(async () => {
    if (!terrainPositions) return;
    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute(
      "position",
      new THREE.BufferAttribute(terrainPositions, 3)
    );

    const nonIndexedIndex = Array.from(
      { length: geometry.getAttribute("position").count },
      (_, index) => index
    );
    geometry.setIndex(nonIndexedIndex);

    const material = new THREE.MeshBasicMaterial({ color: 0x000000 });
    const mesh = new THREE.Mesh(geometry, material);
    const exporter = new GLTFExporter();

    const scene = new THREE.Scene();
    scene.add(mesh);

    exporter.parse(
      scene,
      async (arrayBuffer: ArrayBuffer) => {
        Forma.extensions.storage.setObject({
          key: "terrain.glb",
          data: arrayBuffer,
        });
      },
      undefined,
      { binary: true, forceIndices: true }
    );
  }, [terrainPositions]);

  const buildingsGlbToStorage = useCallback(async () => {
    if (!perBuildingPositions) return;

    const scene = new THREE.Scene();
    const meshes = perBuildingPositions.map((positions) => {
      const geometry = new THREE.BufferGeometry();
      geometry.setAttribute(
        "position",
        new THREE.BufferAttribute(positions, 3)
      );
      const nonIndexedIndex = Array.from(
        { length: geometry.getAttribute("position").count },
        (_, index) => index
      );
      geometry.setIndex(nonIndexedIndex);

      const material = new THREE.MeshBasicMaterial({ color: 0x000000 });
      return new THREE.Mesh(geometry, material);
    });
    scene.add(...meshes);

    const exporter = new GLTFExporter();

    exporter.parse(
      scene,
      async (arrayBuffer: ArrayBuffer) => {
        Forma.extensions.storage.setObject({
          key: "surroundings.glb",
          data: arrayBuffer,
        });
      },
      undefined,
      { binary: true }
    );
  }, [perBuildingPositions]);
  return (
    <div>
      {terrainPositions && (
        <div>
          <button onClick={terrainGlbExportToStorage}>
            Store terrain to extension storage
          </button>
          <button onClick={buildingsGlbToStorage}>
            Store buildings to extension storage
          </button>
        </div>
      )}
    </div>
  );
}

render(<App />, document.getElementById("app"));
