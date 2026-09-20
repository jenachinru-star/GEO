/**
 * 时间格式化工具
 *
 * 后端大部分时间字段（created_at / updated_at）由 SQLite 的 func.now() 生成，
 * 存的是 UTC 时间，但 isoformat() 输出不带时区标记（如 "2026-09-20T06:45:12"）。
 * 前端 new Date() 会把不带时区的字符串按本地时区解析，导致显示比北京时间晚 8 小时。
 *
 * 因此对这类 UTC 字段，前端需要补上 'Z' 让 JS 按 UTC 解析后再转本地时区。
 *
 * 注意：scheduled_at / published_at 等字段后端用 datetime.now() 赋值，
 * 存的本来就是本地时间（UTC+8），不要用 formatUtcTime，直接显示即可。
 */

/** 判断时间字符串是否已带时区标记（Z 或 +08:00 等） */
const hasTimezone = (t: string): boolean => /[zZ]$|[+-]\d{2}:?\d{2}$/.test(t)

/**
 * 格式化 UTC 时间字段（created_at / updated_at 等）
 * 补 Z 后按本地时区显示，解决 UTC 时间晚 8 小时的问题
 */
export const formatUtcTime = (t: string | null | undefined): string => {
  if (!t) return '-'
  const normalized = hasTimezone(t) ? t : t + 'Z'
  return new Date(normalized).toLocaleString('zh-CN')
}

/**
 * 格式化 UTC 时间字段，只显示日期（不带时间）
 */
export const formatUtcDate = (t: string | null | undefined): string => {
  if (!t) return ''
  const normalized = hasTimezone(t) ? t : t + 'Z'
  return new Date(normalized).toLocaleDateString('zh-CN')
}
