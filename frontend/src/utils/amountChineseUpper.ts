/**
 * 金额中文大写（元角分）。
 *
 * 独立成文件是为了让打印件、凭证与测试脚本共用同一实现：
 * 本文件不依赖任何 @/ 别名模块，可直接被 node 引入运行。
 *
 * 规则：
 * - 前导零不输出（1 → 壹，10 → 壹拾，10000 → 壹万）；
 * - 「零」只在确实需要占位时补一个（10001 → 壹万零壹，100000000 → 壹亿）；
 * - 四位一组的「万 / 亿」分段，组内高位缺位且不是最高组时补「零」；
 * - 负数输出「负」前缀。
 */

const CN_DIGITS = ['零', '壹', '贰', '叁', '肆', '伍', '陆', '柒', '捌', '玖']
/** 个 / 拾 / 佰 / 仟（索引 0 为个位，无单位） */
const CN_UNITS = ['', '拾', '佰', '仟']
/** 分段单位：万 / 亿 / 万亿 */
const CN_BIG_UNITS = ['', '万', '亿', '万亿']

/**
 * 四位分组内的转换：1 ~ 9999 → 「壹仟贰佰叁拾肆」。
 * 组内前导零不输出，中间的连续零只补一个「零」。
 */
function convertFourDigits(n: number): string {
  if (!n) return ''
  const digits = String(n).padStart(4, '0')
  let out = ''
  let pendingZero = false
  for (let i = 0; i < 4; i++) {
    const d = Number(digits[i])
    const unit = CN_UNITS[3 - i]
    if (d === 0) {
      // 仅当已经输出过内容、且后面还有非零位时才需要补「零」
      if (out) pendingZero = true
      continue
    }
    if (pendingZero) {
      out += CN_DIGITS[0]
      pendingZero = false
    }
    out += CN_DIGITS[d] + unit
  }
  return out
}

/** 整数部分：按万 / 亿分段输出 */
function convertIntegerPart(n: number): string {
  if (!Number.isFinite(n) || n <= 0) return ''
  const s = String(Math.trunc(n))
  // 每 4 位一组，低位在前
  const groups: number[] = []
  for (let i = s.length; i > 0; i -= 4) {
    groups.unshift(Number(s.slice(Math.max(0, i - 4), i)))
  }
  let out = ''
  let pendingZero = false
  for (let gi = 0; gi < groups.length; gi++) {
    const g = groups[gi]
    const isHighest = gi === 0
    const bigUnit = CN_BIG_UNITS[groups.length - 1 - gi] || ''
    if (g === 0) {
      // 整组为零：低位若还有非零组，需要用「零」占位
      if (!isHighest) pendingZero = true
      continue
    }
    const part = convertFourDigits(g)
    // 本组不足三位（高位缺位）且不是最高组时，同样需要补「零」
    if (pendingZero || (g < 1000 && !isHighest)) out += CN_DIGITS[0]
    pendingZero = false
    out += part + bigUnit
  }
  return out
}

/**
 * 金额转中文大写。
 * @param amount 金额数值（元）
 * @returns 中文大写文本，如「壹万贰仟叁佰肆拾伍元陆角柒分」
 */
export function amountToChineseUpper(amount: number): string {
  if (amount == null || Number.isNaN(amount) || !Number.isFinite(amount)) return ''
  const negative = amount < 0
  // 先取整到分，避免浮点误差
  const fixed = Math.round(Math.abs(amount) * 100) / 100
  const str = fixed.toFixed(2)
  const yuan = Number(str.slice(0, str.indexOf('.')))
  const jiao = Number(str.charAt(str.length - 2))
  const fen = Number(str.charAt(str.length - 1))

  const intText = convertIntegerPart(yuan)
  let tail = '元'
  if (jiao === 0 && fen === 0) {
    tail += '整'
  } else {
    // 有分无角时补一个「零」，如 0.05 → 零元零伍分
    tail += jiao ? `${CN_DIGITS[jiao]}角` : CN_DIGITS[0]
    tail += fen ? `${CN_DIGITS[fen]}分` : '整'
  }
  const body = intText ? `${intText}${tail}` : `零${tail}`
  return negative ? `负${body}` : body
}
