/**
 * 资产坐标契约：解析 OBJ 的几何统计量，供断言测试与三维加载器共用。
 *
 * 设计原则：**不要求建模的人对齐世界坐标**。资产可以有自己的一套局部坐标系，
 * 但它必须登记在 assets.manifest.json 里，由加载层统一吸收。
 * 详见 docs/coords.md 第 7 节。
 */

import { readFileSync } from "node:fs";

export type Vec3 = [number, number, number];

export interface Box {
  min: Vec3;
  max: Vec3;
}

export interface ObjStats {
  /** 每个 object 的包围盒（按面索引回溯顶点，不依赖行序） */
  objects: Record<string, Box>;
  /** 全模型包围盒 */
  box: Box;
  vertexCount: number;
  faceCount: number;
}

export interface AssetEntry {
  up?: string;
  origin?: { note?: string; translateToRearAxle?: Vec3 };
  frontAxleObjects?: string[];
  rearAxleObjects?: string[];
  expect?: Record<string, number | boolean>;
  warnings?: string[];
}

export interface Manifest {
  version: number;
  tolerance: number;
  assets: Record<string, AssetEntry>;
}

export function loadManifest(path = "assets.manifest.json"): Manifest {
  return JSON.parse(readFileSync(path, "utf-8")) as Manifest;
}

/** 解析 OBJ：顶点在前、面在后是通用写法，所以必须按面的索引回去找顶点。 */
export function parseObj(text: string): ObjStats {
  const verts: Vec3[] = [];
  const objectIndices: Record<string, Set<number>> = {};
  let current: string | null = null;
  let faceCount = 0;

  for (const raw of text.split(/\r?\n/)) {
    const line = raw.trim();
    if (line.startsWith("v ")) {
      const p = line.split(/\s+/);
      verts.push([Number(p[1]), Number(p[2]), Number(p[3])]);
    } else if (line.startsWith("o ")) {
      current = line.slice(2).trim();
      objectIndices[current] ??= new Set();
    } else if (line.startsWith("f ") && current) {
      faceCount++;
      for (const token of line.split(/\s+/).slice(1)) {
        const idx = Number(token.split("/")[0]);
        objectIndices[current].add(idx > 0 ? idx - 1 : verts.length + idx);
      }
    }
  }

  const boxOf = (points: Vec3[]): Box => {
    const min: Vec3 = [Infinity, Infinity, Infinity];
    const max: Vec3 = [-Infinity, -Infinity, -Infinity];
    for (const p of points) {
      for (let i = 0; i < 3; i++) {
        if (p[i] < min[i]) min[i] = p[i];
        if (p[i] > max[i]) max[i] = p[i];
      }
    }
    return { min, max };
  };

  const objects: Record<string, Box> = {};
  for (const [name, idxs] of Object.entries(objectIndices)) {
    const pts = [...idxs].filter((i) => i >= 0 && i < verts.length).map((i) => verts[i]);
    if (pts.length) objects[name] = boxOf(pts);
  }

  return { objects, box: boxOf(verts), vertexCount: verts.length, faceCount };
}

export const span = (b: Box, axis: 0 | 1 | 2) => b.max[axis] - b.min[axis];
export const center = (b: Box, axis: 0 | 1 | 2) => (b.min[axis] + b.max[axis]) / 2;

/** 两组轮子的轴向中心 X（用于算轴距、判前后） */
export function axleCenter(obj: Record<string, Box>, names: string[]): number | null {
  const boxes = names.map((n) => obj[n]).filter(Boolean);
  if (!boxes.length) return null;
  const lo = Math.min(...boxes.map((b) => b.min[0]));
  const hi = Math.max(...boxes.map((b) => b.max[0]));
  return (lo + hi) / 2;
}

/**
 * 三维加载器用这一句吸收坐标系差异（Three.js）：
 *
 *   const entry = manifest.assets["models/最简桑塔纳白模.obj"];
 *   geometry.translate(...(entry.origin?.translateToRearAxle ?? [0, 0, 0]));
 *
 * 平移只在加载时执行一次，之后 mesh 直接按后轴位姿放置，不要每帧算偏移。
 */
export function translateVec(entry: AssetEntry): Vec3 {
  return entry.origin?.translateToRearAxle ?? [0, 0, 0];
}
