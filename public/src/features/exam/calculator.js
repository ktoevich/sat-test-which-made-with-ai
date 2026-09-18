/**
 * The graphing calculator: Desmos, floating over the exam the way the digital
 * SAT offers it.
 *
 * The Desmos script is fetched the first time the calculator is opened, so a
 * student who never opens it never downloads it, and a page loaded offline
 * still works. The panel can be dragged by its header, resized from its
 * corner and minimized to its header; the expressions typed into it stay
 * while the module runs.
 */

import { DESMOS_SCRIPT_URL } from '../../config.js';
import { byId, hide, setText, setVisible, show } from '../../core/dom.js';
import { t } from '../../core/i18n.js';

const loadingText = () => t('exam_calculator_loading');
const failedText = () => t('exam_calculator_failed');

/** Margin the panel keeps from the viewport edges while being dragged. */
const EDGE = 8;

let desmosLoading = null;

/** Resolve once `window.Desmos` is available, fetching the script on first use. */
function loadDesmos() {
  if (window.Desmos) return Promise.resolve(window.Desmos);
  if (!desmosLoading) {
    desmosLoading = new Promise((resolve, reject) => {
      const script = document.createElement('script');
      script.src = DESMOS_SCRIPT_URL;
      script.async = true;
      script.addEventListener('load', () => {
        if (window.Desmos) resolve(window.Desmos);
        else reject(new Error('Desmos did not initialise'));
      });
      script.addEventListener('error', () => reject(new Error('Desmos failed to load')));
      document.head.append(script);
    }).catch((error) => {
      // Let the next open try the network again.
      desmosLoading = null;
      throw error;
    });
  }
  return desmosLoading;
}

export class ExamCalculator {
  constructor() {
    this.elements = {
      toggle: byId('calculator-btn'),
      panel: byId('calculator-panel'),
      handle: byId('calculator-handle'),
      close: byId('calculator-close'),
      minimize: byId('calculator-minimize'),
      notice: byId('calculator-notice'),
      host: byId('calculator-host'),
    };
    /** @type {object|null} the Desmos calculator instance, once mounted */
    this.calculator = null;

    this.elements.toggle.addEventListener('click', () => this.toggle());
    this.elements.close.addEventListener('click', () => this.close());
    this.elements.minimize.addEventListener('click', () => this.setMinimized(!this.isMinimized));
    this.#makeDraggable();
    this.#followResizes();
  }

  get isOpen() {
    return !this.elements.panel.classList.contains('hidden');
  }

  get isMinimized() {
    return this.elements.panel.classList.contains('is-minimized');
  }

  toggle() {
    if (this.isOpen) this.close();
    else this.open();
  }

  open() {
    this.setMinimized(false);
    show(this.elements.panel);
    this.elements.toggle.classList.add('is-active');
    this.elements.toggle.setAttribute('aria-expanded', 'true');
    this.#mount();
  }

  close() {
    hide(this.elements.panel);
    this.elements.toggle.classList.remove('is-active');
    this.elements.toggle.setAttribute('aria-expanded', 'false');
  }

  /** Fold the panel to its header, or unfold it to the size it had. */
  setMinimized(minimized) {
    const { panel, minimize } = this.elements;
    panel.classList.toggle('is-minimized', minimized);
    minimize.setAttribute('aria-expanded', String(!minimized));
    if (!minimized) this.calculator?.resize();
  }

  /** A new module starts with an empty calculator, closed. */
  reset() {
    this.close();
    this.calculator?.setBlank();
  }

  async #mount() {
    if (this.calculator) {
      this.calculator.resize();
      return;
    }
    setText(this.elements.notice, loadingText());
    show(this.elements.notice);
    try {
      const Desmos = await loadDesmos();
      if (this.calculator) return;
      this.calculator = Desmos.GraphingCalculator(this.elements.host, {
        border: false,
        expressionsTopbar: true,
        settingsMenu: true,
      });
      hide(this.elements.notice);
    } catch {
      setText(this.elements.notice, failedText());
      setVisible(this.elements.notice, true);
    }
  }

  /** Put the panel's top-left corner at (left, top), kept inside the viewport. */
  #place(left, top) {
    const { panel } = this.elements;
    const maxLeft = Math.max(EDGE, window.innerWidth - panel.offsetWidth - EDGE);
    const maxTop = Math.max(EDGE, window.innerHeight - panel.offsetHeight - EDGE);
    panel.style.left = `${Math.min(Math.max(EDGE, left), maxLeft)}px`;
    panel.style.top = `${Math.min(Math.max(EDGE, top), maxTop)}px`;
    panel.style.right = 'auto';
  }

  /**
   * Drag the panel around by its header, keeping it inside the viewport.
   *
   * The pointer is captured by the header, and while the drag lasts the
   * calculator underneath takes no pointer events, so a fast drag that runs
   * ahead of the panel over the graph is not taken for a pan of the graph and
   * does not lose the panel.
   */
  #makeDraggable() {
    const { panel, handle } = this.elements;
    let grab = null;

    const move = (event) => {
      if (!grab || event.pointerId !== grab.pointerId) return;
      event.preventDefault();
      this.#place(event.clientX - grab.x, event.clientY - grab.y);
    };
    const release = (event) => {
      if (!grab || (event.pointerId !== undefined && event.pointerId !== grab.pointerId)) return;
      try {
        handle.releasePointerCapture?.(grab.pointerId);
      } catch {
        // Already released, for instance by pointercancel.
      }
      grab = null;
      handle.classList.remove('is-dragging');
      panel.classList.remove('is-dragging');
    };

    handle.addEventListener('pointerdown', (event) => {
      if (event.button > 0 || event.target.closest('button')) return;
      const box = panel.getBoundingClientRect();
      grab = { x: event.clientX - box.left, y: event.clientY - box.top, pointerId: event.pointerId };
      try {
        handle.setPointerCapture?.(event.pointerId);
      } catch {
        // Without capture the window listeners below still follow the pointer.
      }
      handle.classList.add('is-dragging');
      panel.classList.add('is-dragging');
      event.preventDefault();
    });
    window.addEventListener('pointermove', move);
    window.addEventListener('pointerup', release);
    window.addEventListener('pointercancel', release);
    handle.addEventListener('lostpointercapture', release);
    // A window made smaller must not leave the panel out of reach.
    window.addEventListener('resize', () => {
      if (!this.isOpen || !panel.style.left) return;
      this.#place(parseFloat(panel.style.left), parseFloat(panel.style.top));
    });
  }

  /** Desmos lays itself out for the window; a panel resized by hand tells it so. */
  #followResizes() {
    if (typeof ResizeObserver !== 'function') return;
    new ResizeObserver(() => this.calculator?.resize()).observe(this.elements.host);
  }
}
