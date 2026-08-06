import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import WelcomeScene from '@/views/home/components/WelcomeScene.vue'

function installMotionPreference(matches = false) {
  vi.stubGlobal('matchMedia', vi.fn(() => ({ matches })))
}

function installAnimationFrame() {
  vi.stubGlobal('requestAnimationFrame', vi.fn(() => 17))
  vi.stubGlobal('cancelAnimationFrame', vi.fn())
}

function installCanvasContext() {
  vi.spyOn(HTMLElement.prototype, 'clientWidth', 'get').mockReturnValue(1280)
  vi.spyOn(HTMLElement.prototype, 'clientHeight', 'get').mockReturnValue(720)
  const context = {
    setTransform: vi.fn(),
    clearRect: vi.fn(),
    beginPath: vi.fn(),
    moveTo: vi.fn(),
    lineTo: vi.fn(),
    closePath: vi.fn(),
    fill: vi.fn(),
    stroke: vi.fn(),
    globalAlpha: 1,
    strokeStyle: '',
    fillStyle: '',
    lineWidth: 1,
  }
  vi.spyOn(HTMLCanvasElement.prototype, 'getContext').mockReturnValue(context)
  return context
}

describe('welcome investment scene', () => {
  beforeEach(() => {
    installMotionPreference(false)
    installAnimationFrame()
  })

  afterEach(() => {
    vi.restoreAllMocks()
    vi.unstubAllGlobals()
  })

  it('renders the layered apparatus and 2.5D energy assets', () => {
    installCanvasContext()
    const wrapper = mount(WelcomeScene)

    expect(wrapper.find('.ir-scene-layer--atmosphere').exists()).toBe(true)
    expect(wrapper.find('.ir-scene-layer--devices').exists()).toBe(true)
    expect(wrapper.find('.ir-scene-layer--paths').exists()).toBe(true)
    expect(wrapper.find('.ir-scene-layer--apparatus').exists()).toBe(true)
    expect(wrapper.find('.ir-scene-cabinet--main').exists()).toBe(true)
    expect(wrapper.findAll('.ir-scene-cabinet')).toHaveLength(3)
    expect(wrapper.find('.ir-scene-wind').exists()).toBe(true)
    expect(wrapper.find('.ir-scene-solar').exists()).toBe(true)
    expect(wrapper.find('.ir-scene-grid-node--main').exists()).toBe(true)
    expect(wrapper.find('canvas').exists()).toBe(true)
  })

  it('treats a throwing canvas context as an unavailable particle layer', () => {
    vi.spyOn(HTMLElement.prototype, 'clientWidth', 'get').mockReturnValue(1280)
    vi.spyOn(HTMLElement.prototype, 'clientHeight', 'get').mockReturnValue(720)
    vi.spyOn(HTMLCanvasElement.prototype, 'getContext').mockImplementation(() => {
      throw new Error('canvas unavailable')
    })

    expect(() => mount(WelcomeScene)).not.toThrow()
    expect(requestAnimationFrame).not.toHaveBeenCalled()
  })

  it('does not start canvas motion when reduced motion is requested', () => {
    installMotionPreference(true)
    const getContext = vi.spyOn(HTMLCanvasElement.prototype, 'getContext')

    mount(WelcomeScene)

    expect(getContext).not.toHaveBeenCalled()
    expect(requestAnimationFrame).not.toHaveBeenCalled()
  })

  it('pauses and resumes canvas work with page visibility', () => {
    installCanvasContext()
    let hidden = false
    vi.spyOn(document, 'hidden', 'get').mockImplementation(() => hidden)
    mount(WelcomeScene)

    expect(requestAnimationFrame).toHaveBeenCalledTimes(1)

    hidden = true
    document.dispatchEvent(new Event('visibilitychange'))
    expect(cancelAnimationFrame).toHaveBeenCalledWith(17)

    const callsBeforeResume = requestAnimationFrame.mock.calls.length
    hidden = false
    document.dispatchEvent(new Event('visibilitychange'))
    expect(requestAnimationFrame.mock.calls.length).toBeGreaterThan(callsBeforeResume)
  })

  it('removes scene listeners and animation work when unmounted', () => {
    installCanvasContext()
    const removeWindowListener = vi.spyOn(window, 'removeEventListener')
    const removeDocumentListener = vi.spyOn(document, 'removeEventListener')
    const wrapper = mount(WelcomeScene)

    wrapper.unmount()

    expect(cancelAnimationFrame).toHaveBeenCalledWith(17)
    expect(removeWindowListener).toHaveBeenCalledWith('resize', expect.any(Function))
    expect(removeDocumentListener).toHaveBeenCalledWith('visibilitychange', expect.any(Function))
  })
})
