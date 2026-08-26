<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { allowsMotion } from '../accessibility'

// 首页 3D 网络英雄区：three.js 渲染的可旋转「社会网络」球-边结构。
// WebGL 不可用或 prefers-reduced-motion 时退回静态网络插画，绝不阻塞首屏。
const container = ref<HTMLDivElement | null>(null)
const active = ref(false)
let cleanup: (() => void) | null = null

onMounted(async () => {
  const host = container.value
  if (!host || typeof document === 'undefined') return
  let disposeThis: (() => void) | null = null
  try {
    const THREE = await import('three')
    const scene = new THREE.Scene()
    const camera = new THREE.PerspectiveCamera(42, 1, 0.1, 100)
    camera.position.set(0, 0.4, 7.6)

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true })
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2))
    renderer.setSize(host.clientWidth || 1, host.clientHeight || 1, false)
    host.appendChild(renderer.domElement)

    const group = new THREE.Group()
    scene.add(group)

    // 确定性伪随机：同一构建每次看到的网络形态一致。
    let state = 20260827
    const nextRandom = () => {
      state = (state * 1_103_515_245 + 12_345) % 2_147_483_648
      return state / 2_147_483_648
    }

    const nodeCount = 52
    const nodeColors = [0x0f6b4f, 0x0d8a63, 0x6d5a8e, 0xe8930c, 0x2f9e8f]
    const positions: Array<[number, number, number]> = []
    const nodeMeshes: Array<{ mesh: import('three').Mesh; phase: number }> = []
    const sphereGeometry = new THREE.SphereGeometry(1, 20, 20)
    for (let index = 0; index < nodeCount; index += 1) {
      // 球面 Fibonacci 分布 + 抖动：均匀又不机械。
      const offset = 2 / nodeCount
      const increment = Math.PI * (3 - Math.sqrt(5))
      const y = index * offset - 1 + offset / 2
      const radius = Math.sqrt(Math.max(0, 1 - y * y))
      const theta = increment * index
      const jitter = 0.55
      positions.push([
        Math.cos(theta) * radius * 2.7 + (nextRandom() - 0.5) * jitter,
        y * 2.7 + (nextRandom() - 0.5) * jitter,
        Math.sin(theta) * radius * 2.7 + (nextRandom() - 0.5) * jitter,
      ])
    }

    const edgeEndpoints: number[] = []
    for (let index = 0; index < nodeCount; index += 1) {
      const [x, y, z] = positions[index]
      const nodeScale = 0.085 + nextRandom() * 0.13
      const color = nodeColors[index % nodeColors.length]
      const material = new THREE.MeshStandardMaterial({ color, roughness: 0.32, metalness: 0.08, emissive: color, emissiveIntensity: 0.22 })
      const mesh = new THREE.Mesh(sphereGeometry, material)
      mesh.position.set(x, y, z)
      mesh.scale.setScalar(nodeScale)
      group.add(mesh)
      nodeMeshes.push({ mesh, phase: nextRandom() * Math.PI * 2 })

      // 每个节点连到最近的两三个邻居，形成自然的社区式连边。
      const distances = positions
        .map((target, targetIndex) => ({
          targetIndex,
          distance: (target[0] - x) ** 2 + (target[1] - y) ** 2 + (target[2] - z) ** 2,
        }))
        .filter((item) => item.targetIndex !== index)
        .sort((left, right) => left.distance - right.distance)
      const degree = 2 + (index % 2)
      for (let neighbor = 0; neighbor < degree && neighbor < distances.length; neighbor += 1) {
        const other = distances[neighbor].targetIndex
        if (index < other) {
          edgeEndpoints.push(x, y, z, positions[other][0], positions[other][1], positions[other][2])
        }
      }
    }
    const edgeGeometry = new THREE.BufferGeometry()
    edgeGeometry.setAttribute('position', new THREE.Float32BufferAttribute(edgeEndpoints, 3))
    const edges = new THREE.LineSegments(edgeGeometry, new THREE.LineBasicMaterial({ color: 0x9fb0a6, transparent: true, opacity: 0.45 }))
    group.add(edges)

    scene.add(new THREE.AmbientLight(0xffffff, 0.9))
    const keyLight = new THREE.DirectionalLight(0xffffff, 1.25)
    keyLight.position.set(4, 5, 6)
    scene.add(keyLight)
    const rimLight = new THREE.DirectionalLight(0xcfe8dc, 0.55)
    rimLight.position.set(-5, -2, -4)
    scene.add(rimLight)

    let pointerX = 0
    let pointerY = 0
    const onPointerMove = (event: PointerEvent) => {
      const bounds = host.getBoundingClientRect()
      pointerX = ((event.clientX - bounds.left) / Math.max(1, bounds.width) - 0.5) * 2
      pointerY = ((event.clientY - bounds.top) / Math.max(1, bounds.height) - 0.5) * 2
    }
    host.addEventListener('pointermove', onPointerMove)

    const resize = () => {
      const width = host.clientWidth || 1
      const height = host.clientHeight || 1
      renderer.setSize(width, height, false)
      camera.aspect = width / height
      camera.updateProjectionMatrix()
    }
    resize()
    const observer = new ResizeObserver(resize)
    observer.observe(host)

    const reducedMotion = !allowsMotion()
    let frame = 0
    let stopped = false
    const clock = new THREE.Clock()
    const renderFrame = () => {
      if (stopped) return
      frame = requestAnimationFrame(renderFrame)
      const elapsed = clock.getElapsedTime()
      if (!reducedMotion) {
        for (const node of nodeMeshes) {
          node.mesh.position.y += Math.sin(elapsed * 0.9 + node.phase) * 0.0022
        }
      }
      group.rotation.y = reducedMotion ? 0.5 : elapsed * 0.16 + pointerX * 0.35
      group.rotation.x = reducedMotion ? -0.15 : -pointerY * 0.25
      renderer.render(scene, camera)
    }
    renderFrame()
    active.value = true

    disposeThis = () => {
      stopped = true
      cancelAnimationFrame(frame)
      observer.disconnect()
      host.removeEventListener('pointermove', onPointerMove)
      sphereGeometry.dispose()
      edgeGeometry.dispose()
      const edgeMaterial = edges.material as import('three').Material
      edgeMaterial.dispose()
      for (const node of nodeMeshes) {
        const material = node.mesh.material as import('three').Material
        material.dispose()
      }
      renderer.dispose()
      renderer.domElement.remove()
    }
  } catch {
    // WebGL 初始化失败（无 GPU / 测试环境）：保持静态 SVG 兜底。
    disposeThis?.()
  }
  cleanup = disposeThis
})

onBeforeUnmount(() => cleanup?.())
</script>

<template>
  <div class="network-hero">
    <svg v-show="!active" class="network-hero-fallback" viewBox="0 0 360 220" role="img" aria-label="社会网络示意图：节点代表行动者，连线代表关系，颜色代表社区">
      <g stroke="#8fae9f" stroke-width="1.5" opacity="0.7">
        <line x1="64" y1="62" x2="128" y2="38" /><line x1="64" y1="62" x2="118" y2="104" /><line x1="64" y1="62" x2="52" y2="126" />
        <line x1="128" y1="38" x2="186" y2="66" /><line x1="118" y1="104" x2="186" y2="66" /><line x1="118" y1="104" x2="52" y2="126" />
        <line x1="186" y1="66" x2="248" y2="40" /><line x1="186" y1="66" x2="252" y2="112" /><line x1="186" y1="66" x2="150" y2="158" />
        <line x1="252" y1="112" x2="150" y2="158" /><line x1="252" y1="112" x2="308" y2="70" /><line x1="252" y1="112" x2="312" y2="158" />
        <line x1="308" y1="70" x2="312" y2="158" /><line x1="150" y1="158" x2="92" y2="184" /><line x1="52" y1="126" x2="92" y2="184" />
      </g>
      <g>
        <circle cx="186" cy="66" r="14" fill="#0f6b4f" /><circle cx="252" cy="112" r="11" fill="#0f6b4f" />
        <circle cx="64" cy="62" r="9" fill="#6d5a8e" /><circle cx="128" cy="38" r="7" fill="#6d5a8e" />
        <circle cx="118" cy="104" r="7" fill="#2f9e8f" /><circle cx="248" cy="40" r="7" fill="#2f9e8f" />
        <circle cx="150" cy="158" r="9" fill="#0d8a63" /><circle cx="92" cy="184" r="7" fill="#0d8a63" />
        <circle cx="52" cy="126" r="7" fill="#6d5a8e" /><circle cx="308" cy="70" r="7" fill="#e8930c" />
        <circle cx="312" cy="158" r="7" fill="#e8930c" />
      </g>
    </svg>
    <div ref="container" class="network-hero-canvas" aria-hidden="true" />
    <span v-if="active" class="network-hero-hint">三维关系网络 · 随视线旋转</span>
    <span class="network-hero-chip chip-metric" aria-hidden="true">度中心性 <strong>0.92</strong></span>
    <span class="network-hero-chip chip-community" aria-hidden="true"><i class="dot dot-a" />社区 A<i class="dot dot-b" />社区 B<i class="dot dot-c" />社区 C</span>
  </div>
</template>

<style scoped>
.network-hero {
  position: relative;
  width: 100%;
  min-height: 340px;
  border-radius: var(--radius);
  overflow: hidden;
  border: 1px solid var(--line);
  background:
    radial-gradient(110% 90% at 82% 8%, rgba(109, 90, 142, 0.14), transparent 60%),
    radial-gradient(90% 90% at 8% 92%, rgba(15, 107, 79, 0.12), transparent 58%),
    linear-gradient(160deg, #ffffff 0%, #f3f7f3 100%);
}
.network-hero-fallback { position: absolute; inset: 8% 6%; width: 88%; height: 84%; }
.network-hero-canvas { position: absolute; inset: 0; }
.network-hero-canvas :deep(canvas) { display: block; width: 100% !important; height: 100% !important; }
.network-hero-hint {
  position: absolute;
  left: 50%;
  bottom: 0.75rem;
  transform: translateX(-50%);
  padding: 0.2rem 0.65rem;
  border-radius: 999px;
  background: rgba(247, 242, 232, 0.85);
  color: #33433c;
  font-size: 0.68rem;
  letter-spacing: 0.06em;
  white-space: nowrap;
}
.network-hero-chip {
  position: absolute;
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.42rem 0.8rem;
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.94);
  color: #26332d;
  font-size: 0.72rem;
  font-weight: 600;
  box-shadow: 0 12px 30px rgba(35, 42, 51, 0.16);
  animation: chip-float 5.2s ease-in-out infinite;
}
.network-hero-chip strong { color: #0f6b4f; font-size: 0.8rem; }
.chip-metric { top: 1rem; left: 1rem; }
.chip-community { bottom: 2.7rem; right: 1rem; animation-delay: -2.4s; }
.network-hero-chip .dot { width: 0.5rem; height: 0.5rem; border-radius: 50%; display: inline-block; }
.dot-a { background: #0f6b4f; }
.dot-b { background: #6d5a8e; }
.dot-c { background: #e8930c; }
@keyframes chip-float {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-6px); }
}
@media (prefers-reduced-motion: reduce) {
  .network-hero { min-height: 280px; }
  .network-hero-chip { animation: none; }
}
</style>
