// App State
let currentSection = "";
let questions = [];
let currentQuestionIndex = 0;
let userAnswers = {}; // { questionId: selectedOptionIndex }
let timerInterval = null;
let timeRemaining = 0;

// DOM Elements
const views = {
    landing: document.getElementById('landing-page'),
    test: document.getElementById('test-interface'),
    results: document.getElementById('results-page')
};

const elements = {
    sectionTitle: document.getElementById('section-title'),
    timeText: document.getElementById('time-text'),
    passagePane: document.getElementById('passage-pane'),
    passageText: document.getElementById('passage-text'),
    qNum: document.getElementById('q-num'),
    questionText: document.getElementById('question-text'),
    optionsContainer: document.getElementById('options-container'),
    currentQIndicator: document.getElementById('current-q-indicator'),
    popoverGrid: document.getElementById('popover-grid'),
    questionMapPopover: document.getElementById('question-map-popover'),
    testContent: document.querySelector('.test-content')
};

// Event Listeners
document.getElementById('start-rw-btn').addEventListener('click', () => startSection('Reading & Writing', 32 * 60));
document.getElementById('start-math-btn').addEventListener('click', () => startSection('Math', 35 * 60));
document.getElementById('next-btn').addEventListener('click', goNext);
document.getElementById('prev-btn').addEventListener('click', goPrev);
document.getElementById('finish-btn').addEventListener('click', finishSection);
document.getElementById('q-map-btn').addEventListener('click', togglePopover);
document.getElementById('home-btn').addEventListener('click', goHome);

// Functions
function switchView(viewName) {
    Object.values(views).forEach(v => v.classList.remove('active'));
    views[viewName].classList.add('active');
}

function startSection(sectionName, timeInSeconds) {
    currentSection = sectionName;
    questions = questionsData[sectionName];
    currentQuestionIndex = 0;
    userAnswers = {};
    timeRemaining = timeInSeconds;
    
    elements.sectionTitle.textContent = sectionName;
    
    // Math doesn't typically have long passages on the left in the same way, we can hide passage pane if empty
    if (sectionName === "Math") {
        elements.testContent.classList.add('full-width');
    } else {
        elements.testContent.classList.remove('full-width');
    }

    switchView('test');
    loadQuestion();
    startTimer();
    renderMapPopover();
}

function loadQuestion() {
    const q = questions[currentQuestionIndex];
    
    // Update Passage
    if (q.passage) {
        elements.passageText.innerHTML = `<p>${q.passage}</p>`;
        elements.testContent.classList.remove('full-width');
    } else {
        elements.passageText.innerHTML = "";
        elements.testContent.classList.add('full-width');
    }

    // Update Question
    elements.qNum.textContent = currentQuestionIndex + 1;
    elements.questionText.textContent = q.question;
    
    // Update Options
    elements.optionsContainer.innerHTML = "";
    q.options.forEach((optText, index) => {
        const btn = document.createElement('div');
        btn.className = 'option-btn';
        if (userAnswers[q.id] === index) {
            btn.classList.add('selected');
        }
        
        // Extract letter (A, B, C, D) from text if it's there, else generate it
        let letter = String.fromCharCode(65 + index);
        let text = optText;
        if (optText.match(/^[A-D]\)\s/)) {
            letter = optText.charAt(0);
            text = optText.substring(3);
        }

        btn.innerHTML = `<span class="option-letter">${letter}</span> <span class="option-text">${text}</span>`;
        btn.addEventListener('click', () => selectOption(index));
        elements.optionsContainer.appendChild(btn);
    });

    // Update Footer navigation
    elements.currentQIndicator.textContent = `${currentQuestionIndex + 1} of ${questions.length}`;
    updateMapPopoverDots();
}

function selectOption(index) {
    const qId = questions[currentQuestionIndex].id;
    userAnswers[qId] = index;
    loadQuestion(); // Re-render to show selection
}

function goNext() {
    if (currentQuestionIndex < questions.length - 1) {
        currentQuestionIndex++;
        loadQuestion();
    }
}

function goPrev() {
    if (currentQuestionIndex > 0) {
        currentQuestionIndex--;
        loadQuestion();
    }
}

function jumpToQuestion(index) {
    currentQuestionIndex = index;
    loadQuestion();
    elements.questionMapPopover.classList.add('hidden');
}

function togglePopover() {
    elements.questionMapPopover.classList.toggle('hidden');
}

function renderMapPopover() {
    elements.popoverGrid.innerHTML = "";
    questions.forEach((q, idx) => {
        const dot = document.createElement('div');
        dot.className = 'map-dot';
        dot.textContent = idx + 1;
        dot.addEventListener('click', () => jumpToQuestion(idx));
        elements.popoverGrid.appendChild(dot);
    });
}

function updateMapPopoverDots() {
    const dots = elements.popoverGrid.children;
    questions.forEach((q, idx) => {
        dots[idx].className = 'map-dot';
        if (userAnswers[q.id] !== undefined) {
            dots[idx].classList.add('answered');
        }
        if (idx === currentQuestionIndex) {
            dots[idx].classList.add('current');
        }
    });
}

function startTimer() {
    clearInterval(timerInterval);
    updateTimerDisplay();
    timerInterval = setInterval(() => {
        timeRemaining--;
        updateTimerDisplay();
        if (timeRemaining <= 0) {
            finishSection();
        }
    }, 1000);
}

function updateTimerDisplay() {
    const minutes = Math.floor(timeRemaining / 60);
    const seconds = timeRemaining % 60;
    elements.timeText.textContent = `${minutes}:${seconds < 10 ? '0' : ''}${seconds}`;
}

function finishSection() {
    clearInterval(timerInterval);
    
    // Calculate Score
    let correctCount = 0;
    const breakdownContainer = document.getElementById('results-breakdown');
    breakdownContainer.innerHTML = "";

    questions.forEach((q, idx) => {
        const userAns = userAnswers[q.id];
        const isCorrect = userAns === q.correctAnswer;
        if (isCorrect) correctCount++;

        const item = document.createElement('div');
        item.className = 'result-item';
        
        let statusHtml = "";
        if (userAns === undefined) {
            statusHtml = `<span class="result-incorrect">Omitted</span>`;
        } else if (isCorrect) {
            statusHtml = `<span class="result-correct">Correct</span>`;
        } else {
            statusHtml = `<span class="result-incorrect">Incorrect</span>`;
        }

        item.innerHTML = `<span>Question ${idx + 1}</span> ${statusHtml}`;
        breakdownContainer.appendChild(item);
    });

    let scaledScore = 200 + Math.round((600 * (correctCount / questions.length)) / 10) * 10;
    document.getElementById('scaled-score-text').textContent = scaledScore;
    document.getElementById('score-text').textContent = `${correctCount} / ${questions.length}`;
    
    switchView('results');
}

function goHome() {
    switchView('landing');
}
