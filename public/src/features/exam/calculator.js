/**
 * The graphing calculator: Desmos, floating over the exam the way the digital
 * SAT offers it.
 *
 * The Desmos script is fetched the first time the calculator is opened, so a
 * student who never opens it never downloads it, and a page loaded offline
 * still works. The panel can be dragged by its header and resized from its
 * corner; the expressions typed into it stay while the module runs.
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
      notice: byId('calculator-notice'),
      host: byId('calculator-host'),
    };
    /** @type {object|null} the Desmos calculator instance, once mounted */
    this.calculator = null;

    this.elements.toggle.addEventListener('click', () => this.toggle());
    this.elements.close.addEventListener('click', () => this.close());
    this.#makeDraggable();
    this.#followResizes();
  }

  get isOpen() {
    return !this.elements.panel.classList.contains('hidden');
  }

  toggle() {
    if (this.isOpen) this.close();
    else this.open();
  }

  open() {
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

  /** Drag the panel around by its header, keeping it inside the viewport. */
  #makeDraggable() {
    const { panel, handle } = this.elements;
    let grab = null;

    const move = (event) => {
      if (!grab) return;
      const maxLeft = window.innerWidth - panel.offsetWidth - EDGE;
      const maxTop = window.innerHeight - panel.offsetHeight - EDGE;
      const left = Math.min(Math.max(EDGE, event.clientX - grab.x), maxLeft);
      const top = Math.min(Math.max(EDGE, event.clientY - grab.y), maxTop);
      panel.style.left = `${left}px`;
      panel.style.top = `${top}px`;
      panel.style.right = 'auto';
    };
    const release = () => {
      grab = null;
      handle.classList.remove('is-dragging');
    };

    handle.addEventListener('pointerdown', (event) => {
      if (event.target.closest('button')) return;
      const box = panel.getBoundingClientRect();
      grab = { x: event.clientX - box.left, y: event.clientY - box.top };
      handle.classList.add('is-dragging');
      event.preventDefault();
    });
    window.addEventListener('pointermove', move);
    window.addEventListener('pointerup', release);
    window.addEventListener('pointercancel', release);
  }

  /** Desmos lays itself out for the window; a panel resized by hand tells it so. */
  #followResizes() {
    if (typeof ResizeObserver !== 'function') return;
    new ResizeObserver(() => this.calculator?.resize()).observe(this.elements.host);
  }
}
