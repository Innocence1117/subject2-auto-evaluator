/**
 * 资产坐标契约测试 —— 不需要 Three.js，纯文本解析 OBJ。
 *
 * 它防的是同一类事故：模型被重新导出/替换后，原点或尺寸悄悄变了，
 * 于是画面上车轮压线、判定却说没压（或反过来）。
 * 一旦对不上，这条测试立刻红，而不是等到答辩前才发现。
 */

import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

import {
  axleCenter,
  loadManifest,
  parseObj,
  span,
  translateVec,
} from "./modelContract";

const manifest = loadManifest();
const tol = manifest.tolerance ?? 0.001;

describe("资产坐标契约", () => {
  for (const [path, entry] of Object.entries(manifest.assets)) {
    describe(path, () => {
      const stats = parseObj(readFileSync(path, "utf-8"));
      const expectMap = entry.expect ?? {};

      it("是米制，不是毫米", () => {
        // 毫米模型的车长会是 4473 这种量级，直接挡掉
        expect(span(stats.box, 0)).toBeLessThan(200);
      });

      for (const [key, expected] of Object.entries(expectMap)) {
        if (typeof expected !== "number") continue;
        it(key + " ≈ " + expected, () => {
          let actual: number;
          switch (key) {
            case "lengthX":
              actual = span(stats.box, 0);
              break;
            case "widthZ":
              actual = span(stats.box, 2);
              break;
            case "heightY":
              actual = span(stats.box, 1);
              break;
            case "minY":
              actual = stats.box.min[1];
              break;
            case "wheelbase": {
              const f = axleCenter(stats.objects, entry.frontAxleObjects ?? []);
              const r = axleCenter(stats.objects, entry.rearAxleObjects ?? []);
              expect(f, "找不到前轮 object，检查 frontAxleObjects").not.toBeNull();
              expect(r, "找不到后轮 object，检查 rearAxleObjects").not.toBeNull();
              actual = Math.abs((f as number) - (r as number));
              break;
            }
            case "trackWidth": {
              // 轮距是左右轮【中心】之间的距离，不是外缘到外缘
              const wheels = [
                ...(entry.frontAxleObjects ?? []),
                ...(entry.rearAxleObjects ?? []),
              ]
                .map((n) => stats.objects[n])
                .filter(Boolean);
              expect(wheels.length, "找不到车轮 object").toBeGreaterThan(0);
              const zCenters = wheels.map((b) => (b.min[2] + b.max[2]) / 2);
              actual = Math.max(...zCenters) - Math.min(...zCenters);
              break;
            }
            default:
              throw new Error("manifest 里有测试没实现的字段：" + key);
          }
          expect(Math.abs(actual - expected)).toBeLessThanOrEqual(tol);
        });
      }

      // 原点归位：资产的私有偏移必须被 translate 抵消，抵消后后轴应在 0
      if (entry.rearAxleObjects?.length) {
        it("后轴 + translate 之后落在原点", () => {
          const r = axleCenter(stats.objects, entry.rearAxleObjects as string[]);
          expect(r).not.toBeNull();
          const t = translateVec(entry)[0];
          expect(Math.abs((r as number) + t)).toBeLessThanOrEqual(tol);
        });
      }

      if (expectMap.leftIsNegativeZ) {
        it("左侧车轮在 -Z", () => {
          const left = (entry.frontAxleObjects ?? []).filter((n) => n.endsWith("_L"));
          expect(left.length, "找不到左侧车轮 object").toBeGreaterThan(0);
          for (const name of left) {
            expect(stats.objects[name].max[2]).toBeLessThan(0);
          }
        });
      }

      if (entry.warnings?.length) {
        it("有已登记的已知问题（不阻塞 CI，仅提示）", () => {
          for (const w of entry.warnings as string[]) {
            console.warn("[" + path + "] " + w);
          }
          expect(entry.warnings?.length).toBeGreaterThan(0);
        });
      }
    });
  }
});
