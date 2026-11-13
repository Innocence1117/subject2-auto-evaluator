import { expect, test } from 'vitest';
import { TrackConfigSchema } from './schema';

test('测试 zod 拦截非法数据', () => {
  // 准备一份故意写错的数据：把 length 写成了字符串 "4.473"
  const badData = {
    id: "test_01",
    vehicle: {
      length: "4.473", // 错误在这里,应该是数字
      width: 1.706,
      wheelbase: 2.548
    },
    lines: []
  };

  // 使用 safeParse 进行校验
  const result = TrackConfigSchema.safeParse(badData);

  // 断言：校验必须失败
  expect(result.success).toBe(false);

  // 顺便把错误打印出来看看
  if (!result.success) {
    console.log("Zod 发现了错误：", result.error.issues[0].message);
  }
});