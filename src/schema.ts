import { z } from "zod";

// 定义点的结构
export const Vec2Schema = z.object({
  x: z.number(),
  y: z.number(),
});

// 定义车辆参数的结构
export const VehicleSpecSchema = z.object({
  length: z.number().positive(), 
  width: z.number().positive(),
  wheelbase: z.number(),
});

// 定义场地线的结构
export const FieldLineSchema = z.object({
  id: z.string(),
  a: Vec2Schema,
  b: Vec2Schema,
  width: z.number(),
});

// 定义整体考场配置的结构
export const TrackConfigSchema = z.object({
  id: z.string(),
  vehicle: VehicleSpecSchema,
  lines: z.array(FieldLineSchema),
});