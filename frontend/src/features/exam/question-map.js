/** The "N of M" navigator popup listing every question in the module. */

import { byId, clear, el, hide, setText } from '../../core/dom.js';
import { isAnswered } from '../../core/questions.js';

export class QuestionMap {
  /** @param {{ onSelect: (index: number) => void }} options */
  constructor({ onSelect }) {
    this.onSelect = onSelect;
    this.elements = {
      trigger: byId('tracker-btn'),
      popup: byId('question-map'),
      grid: byId('question-map-grid'),
    };

    this.elements.trigger.addEventListener('click', (event) => {
      event.stopPropagation();
      this.elements.popup.classList.toggle('hidden');
    });

    document.addEventListener('click', (event) => {
      const insidePopup = this.elements.popup.contains(event.target);
      const onTrigger = this.elements.trigger.contains(event.target);
      if (!insidePopup && !onTrigger) this.close();
    });
  }

  close() {
    hide(this.elements.popup);
  }

  /** Rebuild the grid for a newly loaded module. */
  build(size) {
    clear(this.elements.grid);
    for (let index = 0; index < size; index += 1) {
      const button = el('button', { type: 'button', className: 'map-btn', text: index + 1 });
      button.addEventListener('click', () => {
        this.onSelect(index);
        this.close();
      });
      this.elements.grid.append(button);
    }
  }

  /** @param {import('./exam-state.js').ExamSession['module']} module */
  update(module) {
    setText(this.elements.trigger, `${module.currentIndex + 1} of ${module.size}`);

    [...this.elements.grid.children].forEach((button, index) => {
      button.className = 'map-btn';
      button.classList.toggle('is-active', index === module.currentIndex);
      button.classList.toggle('is-answered', isAnswered(module.answerAt(index)));
      button.classList.toggle('is-flagged', module.isFlagged(index));
    });
  }
}
