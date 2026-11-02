/**
 * 金额中文大写算法测试（独立可运行脚本）。
 *
 * 运行方式（无需 npm 脚本，Node 22+ 直接执行 TypeScript）：
 *   cd frontend && node scripts/test_amount_chinese_upper.ts
 */
import { amountToChineseUpper } from '../src/utils/amountChineseUpper.ts'

type Case = {
  amount: number
  expected: string
  note?: string
}

const CASES: Case[] = [
  { amount: 0, expected: '零元整', note: '零' },
  { amount: 0.05, expected: '零元零伍分', note: '有分无角需补零' },
  { amount: 0.5, expected: '零元伍角整', note: '角位' },
  { amount: 1, expected: '壹元整', note: '前导零不得输出' },
  { amount: 10, expected: '壹拾元整', note: '拾位' },
  { amount: 11, expected: '壹拾壹元整' },
  { amount: 100, expected: '壹佰元整' },
  { amount: 101, expected: '壹佰零壹元整', note: '中间零只补一个' },
  { amount: 500, expected: '伍佰元整' },
  { amount: 1000, expected: '壹仟元整' },
  { amount: 1010, expected: '壹仟零壹拾元整' },
  { amount: 10000, expected: '壹万元整', note: '万位' },
  { amount: 10001, expected: '壹万零壹元整', note: '万位分段补零' },
  { amount: 10010, expected: '壹万零壹拾元整' },
  { amount: 100000, expected: '壹拾万元整', note: '十万' },
  { amount: 1000000, expected: '壹佰万元整', note: '百万' },
  { amount: 1000000.5, expected: '壹佰万元伍角整', note: '百万带角' },
  { amount: 100000000, expected: '壹亿元整', note: '亿位' },
  { amount: 100000001, expected: '壹亿零壹元整' },
  { amount: 100010000, expected: '壹亿零壹万元整' },
  { amount: 1234567.89, expected: '壹佰贰拾叁万肆仟伍佰陆拾柒元捌角玖分' },
  { amount: -500, expected: '负伍佰元整', note: '负数前缀' },
  { amount: -0.07, expected: '负零元零柒分' },
  { amount: 1000.1, expected: '壹仟元壹角整' },
  { amount: 10000.05, expected: '壹万元零伍分' },
]

let failed = 0
for (const c of CASES) {
  const actual = amountToChineseUpper(c.amount)
  if (actual !== c.expected) {
    failed += 1
    console.error(
      `✗ ${c.amount} → 期望「${c.expected}」，实际「${actual}」${c.note ? `（${c.note}）` : ''}`,
    )
  } else {
    console.log(`✓ ${c.amount} → ${actual}`)
  }
}

// 非法输入不应抛错
for (const bad of [NaN, Infinity, -Infinity]) {
  const out = amountToChineseUpper(bad)
  if (out !== '') {
    failed += 1
    console.error(`✗ 非法输入 ${bad} 应返回空串，实际「${out}」`)
  }
}

if (failed) {
  console.error(`\n金额中文大写测试失败：${failed} 项`)
  process.exit(1)
}
console.log(`\n金额中文大写测试通过：${CASES.length} 项边界值全部符合预期`)
