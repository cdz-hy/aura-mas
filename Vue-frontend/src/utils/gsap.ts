import gsap from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'
import { Flip } from 'gsap/Flip'
import { onUnmounted, type Ref } from 'vue'

gsap.registerPlugin(ScrollTrigger, Flip)

// 全局默认
gsap.defaults({
  duration: 0.5,
  ease: 'power2.out',
})

/**
 * 创建 GSAP context，组件卸载时自动清理所有动画
 * @param scope - 可选，限制 context 作用范围的元素或 ref
 */
export function useGsapContext(scope?: Element | Ref<Element | null>) {
  const el = scope && 'value' in scope ? scope.value : scope
  const ctx = gsap.context(() => {}, el)
  onUnmounted(() => ctx.revert())
  return ctx
}

/**
 * 数字计数器动画
 * @param target - 包含 value 属性的响应式对象
 * @param endValue - 目标数值
 * @param options - duration, delay, decimals 等
 */
export function animateCounter(
  target: { value: number },
  endValue: number,
  options: { duration?: number; delay?: number; decimals?: number } = {}
) {
  const { duration = 1.2, delay = 0, decimals = 0 } = options
  const obj = { val: 0 }
  return gsap.to(obj, {
    val: endValue,
    duration,
    delay,
    ease: 'power2.out',
    onUpdate() {
      target.value = decimals > 0
        ? parseFloat(obj.val.toFixed(decimals))
        : Math.round(obj.val)
    },
  })
}

export { gsap, ScrollTrigger, Flip }
