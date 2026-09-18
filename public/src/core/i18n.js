/**
 * The interface in English or Russian.
 *
 * Only the interface: questions, passages and solutions stay as the bank has
 * them. Static markup carries `data-i18n` (text), `data-i18n-placeholder` or
 * `data-i18n-title` attributes and is translated in place; code that builds
 * text asks `t()`. Switching the language re-translates the page and fires a
 * `languagechange` event on the document, so screens that render dynamic
 * text can redraw.
 */

const STORAGE_KEY = 'sat_lang';
export const LANGUAGES = ['en', 'ru'];
export const DEFAULT_LANGUAGE = 'en';

const STRINGS = {
  en: {
    brand: 'Digital SAT practice',
    nav_messages: 'Messages',
    nav_profile: 'Profile',
    nav_logout: 'Logout',
    nav_theme: 'Switch between light and dark',
    lobby_notice_loading: 'Loading your history...',
    lobby_notice_failed: 'Could not load your history.',
    history_empty: "You haven't taken any tests yet. It's time to start!",
    history_empty_other: 'No tests taken yet.',
    history_title: 'Your recent tests',
    history_title_other: "{name}'s tests",
    profile_settings: 'Settings',
    profile_friends: 'Friends',
    profile_messages: 'Messages',
    profile_add_friend: 'Add friend',
    profile_request_sent: 'Request sent',
    profile_accept_request: 'Accept request',
    profile_friends_since: 'Friends ✓',
    profile_unfriend: 'Remove friend',
    profile_message: 'Message',
    profile_since: 'Since {date}',
    profile_location_unset: 'Location not set',
    observer_back: 'My profile',
    stat_rating: 'Rating',
    stat_max_rating: 'Peak rating',
    stat_friends: 'Friends',
    stat_tests: 'Tests taken',
    stat_best_math: 'Best Math',
    stat_best_reading: 'Best Reading & Writing',
    stat_average: 'Average score',
    chart_rating_title: 'Rating over time',
    chart_rating_empty: 'Finish a test to start the rating graph.',
    chart_tests: 'Tests:',
    chart_peak: 'Peak:',
    chart_best_gain: 'Best gain:',
    chart_average: 'Average score:',
    chart_topics_title: 'Questions right by domain',
    chart_topics_empty: 'Domains appear here once a test is finished. Click a domain to practise it.',
    chart_mode_circle: 'Circle',
    chart_mode_bars: 'Bars',
    chart_right_of: '{right} of {seen}',
    chart_total_right: 'right',
    tier_basic: 'Basic',
    tier_intermediate: 'Intermediate',
    tier_advanced: 'Advanced',
    tier_elite: 'Elite',
    tier_basic_full: 'Basic Digital SAT',
    tier_intermediate_full: 'Intermediate Digital SAT (500+)',
    tier_advanced_full: 'Advanced Digital SAT (600+)',
    tier_elite_full: 'Elite Digital SAT (700+)',
    chart_tier: 'Tier:',
    tests_title: 'Practice tests',
    tests_subtitle: 'Two adaptive modules, timed as on the real test. Every question comes from the College Board question bank.',
    test_math_title: 'Math',
    test_math_desc: '2 modules × 22 questions, 35 minutes each, with the Desmos calculator. Module 2 adapts to your Module 1.',
    test_reading_title: 'Reading and Writing',
    test_reading_desc: '2 modules × 27 questions, 32 minutes each. A short passage and one question about it, grouped by domain.',
    test_badge_adaptive: 'Adaptive',
    test_badge_math_time: '70 min • 44 questions',
    test_badge_reading_time: '64 min • 54 questions',
    test_practice_hint: 'Practise a domain:',
    test_start_math: 'Start Math',
    test_start_reading: 'Start Reading & Writing',
    col_date: 'Date',
    col_section: 'Section',
    col_score: 'Score',
    col_correct: 'Correct',
    col_time: 'Time',
    col_rating: 'Rating',
    col_difficulty: 'Difficulty',
    col_status: 'Status',
    col_action: 'Action',
    btn_details: 'Details',
    btn_retake: 'Retake',
    btn_take_test: 'Take this test',
    btn_close: 'Close',
    btn_cancel: 'Cancel',
    btn_save: 'Save changes',
    btn_send: 'Send',
    section_math: 'Math',
    section_reading: 'Reading and Writing',
    section_reading_short: 'R&W',
    side_platform: 'Platform',
    side_students: 'students',
    side_tests: 'tests taken',
    side_perfect: 'scored 800',
    side_average: 'average',
    side_countries: 'Where students are from',
    side_no_countries: 'Nobody has set a location yet.',
    side_leaderboard: 'Leaderboard',
    side_leaderboard_hint: 'Best score per student; quickest first on ties.',
    side_leaderboard_empty: 'No results yet. Be the first!',
    side_search: 'Find students',
    side_search_placeholder: 'Handle or name...',
    side_search_empty: 'Nobody found.',
    settings_title: 'Profile settings',
    settings_avatar: 'Avatar',
    settings_username: 'Handle',
    settings_fullname: 'Full name',
    settings_location: 'Country, city',
    settings_saved: 'Profile updated.',
    friends_title: 'Friends',
    friends_tab_list: 'My friends',
    friends_tab_incoming: 'Requests',
    friends_tab_outgoing: 'Sent',
    friends_tab_find: 'Find',
    friends_empty: 'No friends yet. Find students and send a request.',
    friends_incoming_empty: 'No requests waiting.',
    friends_outgoing_empty: 'No requests sent.',
    friends_accept: 'Accept',
    friends_decline: 'Decline',
    friends_cancel: 'Cancel',
    friends_add: 'Add',
    friends_added: 'Sent',
    messages_title: 'Messages',
    messages_empty: 'No conversations yet. Open a student\'s profile to write to them.',
    messages_pick: 'Pick a conversation.',
    messages_placeholder: 'Write a message...',
    messages_none_yet: 'No messages yet. Say hi!',
    practice_title: 'Practice: {domain}',
    practice_progress: 'Question {n} of {total} • checked as you go',
    practice_check: 'Check answer',
    practice_next: 'Next question',
    practice_finish: 'Finish',
    practice_pick: 'Pick or type an answer first.',
    practice_correct: 'Correct!',
    practice_incorrect: 'Not quite. The answer is {answer}.',
    practice_done_title: 'Practice finished',
    practice_done_body: 'You got {right} of {total} right in {domain}.',
    practice_empty: 'No questions for this domain right now.',
    practice_loading: 'Loading questions...',
    exam_module: '{section}: Module {n}',
    exam_flag: 'Mark for Review',
    exam_calculator: 'Calculator',
    exam_prev: 'Previous',
    exam_next: 'Next',
    exam_finish: 'Finish',
    exam_of: '{n} of {total}',
    exam_answer_placeholder: 'Enter your answer...',
    exam_eliminate: 'Cross out option {letter}',
    exam_restore: 'Restore option {letter}',
    exam_calculator_loading: 'Loading the calculator…',
    exam_calculator_failed: 'The calculator could not be loaded. Check your connection and try again.',
    exam_module_failed: 'Could not load Module {n}.',
    finish_title: 'Are you sure?',
    finish_body: 'You will not be able to return to this module. Are you sure you want to finish?',
    finish_confirm: 'Confirm',
    reload_title: 'Reloading ends the test',
    reload_body: 'The page cannot be reloaded during a test. If you leave now, the questions you have not answered are marked as omitted and the test is scored as it stands.',
    reload_continue: 'Continue the test',
    reload_finish: 'Finish now',
    reload_terminated: 'The page was reloaded during a test, so it was finished with the unanswered questions omitted.',
    results_title: 'Test Complete!',
    results_message: 'Here is your detailed performance summary.',
    results_score_title: 'Your SAT {section} Score',
    results_raw: 'Raw Score:',
    results_rating: 'Rating: {before} → {after}',
    results_breakdown: 'Question Breakdown',
    results_back: 'Return to Lobby',
    results_view: 'View Solution',
    results_not_saved: 'This attempt was not saved.',
    answer_your: 'Your Answer:',
    answer_correct: 'Correct Answer:',
    attempt_title: 'Test Results',
    attempt_breakdown: 'Detailed Breakdown',
    attempt_tested_on: 'Tested on {date}',
    attempt_question: 'Question {n}',
    attempt_no_details: 'No detailed data was saved for this attempt.',
    attempt_details_private: 'Only {name} sees the answers question by question.',
    status_correct: 'Correct',
    status_incorrect: 'Incorrect',
    status_omitted: 'Omitted',
    module_label: 'Module {n}',
    loading_module: 'Module {n} is loading',
    loading_checking: 'Checking for available tests',
    countdown_ready: 'Get ready',
    auth_login: 'Log In',
    auth_register: 'Sign Up',
    auth_welcome: 'Welcome back!',
    auth_welcome_sub: 'Enter your credentials to log in',
    auth_create: 'Create an account',
    auth_create_sub: 'Create a username and password',
    auth_username: 'Username',
    auth_email: 'Email',
    auth_password: 'Password',
    auth_confirm: 'Confirm password',
    auth_busy: 'Please wait...',
    auth_error_missing: 'Please fill in Email and Password.',
    auth_error_username: 'Please enter a username.',
    auth_error_password_short: 'Password must be at least {n} characters.',
    auth_error_password_match: 'Passwords do not match.',
    auth_error_generic: 'Something went wrong. Please try again.',
    time_minutes: '{m} min',
    time_minutes_seconds: '{m} min {s} s',
    time_seconds: '{s} s',
    time_none: '—',
  },
  ru: {
    brand: 'Digital SAT practice',
    nav_messages: 'Сообщения',
    nav_profile: 'Профиль',
    nav_logout: 'Выйти',
    nav_theme: 'Светлая или тёмная тема',
    lobby_notice_loading: 'Загружаем вашу историю...',
    lobby_notice_failed: 'Не удалось загрузить историю.',
    history_empty: 'Вы ещё не проходили тесты. Самое время начать!',
    history_empty_other: 'Тестов пока нет.',
    history_title: 'Ваши последние тесты',
    history_title_other: 'Тесты {name}',
    profile_settings: 'Настройки',
    profile_friends: 'Друзья',
    profile_messages: 'Сообщения',
    profile_add_friend: 'Добавить в друзья',
    profile_request_sent: 'Запрос отправлен',
    profile_accept_request: 'Принять запрос',
    profile_friends_since: 'В друзьях ✓',
    profile_unfriend: 'Удалить из друзей',
    profile_message: 'Написать',
    profile_since: 'С {date}',
    profile_location_unset: 'Город не указан',
    observer_back: 'Мой профиль',
    stat_rating: 'Рейтинг',
    stat_max_rating: 'Максимум',
    stat_friends: 'Друзья',
    stat_tests: 'Сдано тестов',
    stat_best_math: 'Лучший Math',
    stat_best_reading: 'Лучший Reading & Writing',
    stat_average: 'Средний балл',
    chart_rating_title: 'Изменение рейтинга',
    chart_rating_empty: 'Пройдите тест, чтобы график рейтинга появился.',
    chart_tests: 'Тестов:',
    chart_peak: 'Пик:',
    chart_best_gain: 'Лучший прирост:',
    chart_average: 'Средний балл:',
    chart_topics_title: 'Верные ответы по темам',
    chart_topics_empty: 'Темы появятся после первого теста. Нажмите на тему, чтобы потренироваться.',
    chart_mode_circle: 'Круг',
    chart_mode_bars: 'Столбцы',
    chart_right_of: '{right} из {seen}',
    chart_total_right: 'верно',
    tier_basic: 'Базовый',
    tier_intermediate: 'Средний',
    tier_advanced: 'Продвинутый',
    tier_elite: 'Элитный',
    tier_basic_full: 'Базовый Digital SAT',
    tier_intermediate_full: 'Средний Digital SAT (500+)',
    tier_advanced_full: 'Продвинутый Digital SAT (600+)',
    tier_elite_full: 'Элитный Digital SAT (700+)',
    chart_tier: 'Уровень:',
    tests_title: 'Пробные тесты',
    tests_subtitle: 'Два адаптивных модуля с таймером, как на настоящем экзамене. Все вопросы из банка College Board.',
    test_math_title: 'Math',
    test_math_desc: '2 модуля × 22 вопроса по 35 минут, с калькулятором Desmos. Второй модуль подстраивается под результат первого.',
    test_reading_title: 'Reading and Writing',
    test_reading_desc: '2 модуля × 27 вопросов по 32 минуты. Короткий текст и один вопрос к нему, сгруппированные по темам.',
    test_badge_adaptive: 'Адаптивный',
    test_badge_math_time: '70 мин • 44 вопроса',
    test_badge_reading_time: '64 мин • 54 вопроса',
    test_practice_hint: 'Потренировать тему:',
    test_start_math: 'Начать Math',
    test_start_reading: 'Начать Reading & Writing',
    col_date: 'Дата',
    col_section: 'Секция',
    col_score: 'Балл',
    col_correct: 'Верно',
    col_time: 'Время',
    col_rating: 'Рейтинг',
    col_difficulty: 'Сложность',
    col_status: 'Статус',
    col_action: 'Действие',
    btn_details: 'Разбор',
    btn_retake: 'Пересдать',
    btn_take_test: 'Пройти этот тест',
    btn_close: 'Закрыть',
    btn_cancel: 'Отмена',
    btn_save: 'Сохранить',
    btn_send: 'Отправить',
    section_math: 'Math',
    section_reading: 'Reading and Writing',
    section_reading_short: 'R&W',
    side_platform: 'Платформа',
    side_students: 'учеников',
    side_tests: 'тестов сдано',
    side_perfect: 'набрали 800',
    side_average: 'средний балл',
    side_countries: 'География учеников',
    side_no_countries: 'Пока никто не указал город.',
    side_leaderboard: 'Лидеры',
    side_leaderboard_hint: 'Лучший балл каждого; при равенстве — кто быстрее.',
    side_leaderboard_empty: 'Результатов пока нет. Будьте первым!',
    side_search: 'Найти ученика',
    side_search_placeholder: 'Ник или имя...',
    side_search_empty: 'Никого не найдено.',
    settings_title: 'Настройки профиля',
    settings_avatar: 'Аватар',
    settings_username: 'Ник',
    settings_fullname: 'Имя и фамилия',
    settings_location: 'Страна, город',
    settings_saved: 'Профиль обновлён.',
    friends_title: 'Друзья',
    friends_tab_list: 'Мои друзья',
    friends_tab_incoming: 'Заявки',
    friends_tab_outgoing: 'Отправленные',
    friends_tab_find: 'Найти',
    friends_empty: 'Друзей пока нет. Найдите учеников и отправьте заявку.',
    friends_incoming_empty: 'Входящих заявок нет.',
    friends_outgoing_empty: 'Отправленных заявок нет.',
    friends_accept: 'Принять',
    friends_decline: 'Отклонить',
    friends_cancel: 'Отменить',
    friends_add: 'Добавить',
    friends_added: 'Отправлено',
    messages_title: 'Сообщения',
    messages_empty: 'Диалогов пока нет. Откройте профиль ученика, чтобы написать ему.',
    messages_pick: 'Выберите диалог.',
    messages_placeholder: 'Напишите сообщение...',
    messages_none_yet: 'Сообщений пока нет. Поздоровайтесь!',
    practice_title: 'Тренировка: {domain}',
    practice_progress: 'Вопрос {n} из {total} • проверка сразу',
    practice_check: 'Проверить',
    practice_next: 'Следующий вопрос',
    practice_finish: 'Завершить',
    practice_pick: 'Сначала выберите или введите ответ.',
    practice_correct: 'Верно!',
    practice_incorrect: 'Неверно. Правильный ответ: {answer}.',
    practice_done_title: 'Тренировка завершена',
    practice_done_body: 'Вы решили {right} из {total} по теме {domain}.',
    practice_empty: 'Сейчас нет вопросов по этой теме.',
    practice_loading: 'Загружаем вопросы...',
    exam_module: '{section}: Модуль {n}',
    exam_flag: 'Отметить',
    exam_calculator: 'Калькулятор',
    exam_prev: 'Назад',
    exam_next: 'Далее',
    exam_finish: 'Завершить',
    exam_of: '{n} из {total}',
    exam_answer_placeholder: 'Введите ответ...',
    exam_eliminate: 'Зачеркнуть вариант {letter}',
    exam_restore: 'Вернуть вариант {letter}',
    exam_calculator_loading: 'Загружаем калькулятор…',
    exam_calculator_failed: 'Не удалось загрузить калькулятор. Проверьте соединение и попробуйте снова.',
    exam_module_failed: 'Не удалось загрузить модуль {n}.',
    finish_title: 'Вы уверены?',
    finish_body: 'Вернуться к этому модулю будет нельзя. Завершить его?',
    finish_confirm: 'Завершить',
    reload_title: 'Обновление завершит тест',
    reload_body: 'Во время теста страницу нельзя обновлять. Если выйти сейчас, вопросы без ответа будут засчитаны как пропущенные, а тест оценён как есть.',
    reload_continue: 'Продолжить тест',
    reload_finish: 'Завершить сейчас',
    reload_terminated: 'Страница была обновлена во время теста, поэтому он завершён: вопросы без ответа засчитаны как пропущенные.',
    results_title: 'Тест завершён!',
    results_message: 'Вот подробный разбор результата.',
    results_score_title: 'Ваш балл SAT {section}',
    results_raw: 'Верных ответов:',
    results_rating: 'Рейтинг: {before} → {after}',
    results_breakdown: 'Разбор по вопросам',
    results_back: 'Вернуться в лобби',
    results_view: 'Решение',
    results_not_saved: 'Эта попытка не сохранена.',
    answer_your: 'Ваш ответ:',
    answer_correct: 'Правильный ответ:',
    attempt_title: 'Результаты теста',
    attempt_breakdown: 'Подробный разбор',
    attempt_tested_on: 'Дата: {date}',
    attempt_question: 'Вопрос {n}',
    attempt_no_details: 'Подробности этой попытки не сохранены.',
    attempt_details_private: 'Ответы по каждому вопросу видит только {name}.',
    status_correct: 'Верно',
    status_incorrect: 'Неверно',
    status_omitted: 'Пропущено',
    module_label: 'Модуль {n}',
    loading_module: 'Загружается модуль {n}',
    loading_checking: 'Ищем доступные тесты',
    countdown_ready: 'Приготовьтесь',
    auth_login: 'Войти',
    auth_register: 'Регистрация',
    auth_welcome: 'С возвращением!',
    auth_welcome_sub: 'Введите данные, чтобы войти',
    auth_create: 'Создать аккаунт',
    auth_create_sub: 'Придумайте ник и пароль',
    auth_username: 'Ник',
    auth_email: 'Email',
    auth_password: 'Пароль',
    auth_confirm: 'Повторите пароль',
    auth_busy: 'Подождите...',
    auth_error_missing: 'Заполните Email и пароль.',
    auth_error_username: 'Введите ник.',
    auth_error_password_short: 'Пароль должен быть не короче {n} символов.',
    auth_error_password_match: 'Пароли не совпадают.',
    auth_error_generic: 'Что-то пошло не так. Попробуйте ещё раз.',
    time_minutes: '{m} мин',
    time_minutes_seconds: '{m} мин {s} с',
    time_seconds: '{s} с',
    time_none: '—',
  },
};

let current = DEFAULT_LANGUAGE;

function readStored() {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    return LANGUAGES.includes(stored) ? stored : null;
  } catch {
    return null;
  }
}

/** The language in use: `en` or `ru`. */
export function currentLanguage() {
  return current;
}

/**
 * A translated string; `{name}` placeholders are filled from `vars`. A key
 * missing in one language falls back to English, then to the key itself,
 * so a typo shows up on screen instead of hiding as an empty label.
 */
export function t(key, vars = {}) {
  const text = STRINGS[current]?.[key] ?? STRINGS.en[key] ?? key;
  return text.replace(/\{(\w+)\}/g, (_, name) => (vars[name] === undefined ? `{${name}}` : String(vars[name])));
}

/** The label of a section in the current language. */
export function sectionName(sectionKey, { short = false } = {}) {
  if (sectionKey === 'reading') return t(short ? 'section_reading_short' : 'section_reading');
  return t('section_math');
}

/** Translate every marked element under `root`. */
export function applyTranslations(root = document) {
  root.querySelectorAll('[data-i18n]').forEach((element) => {
    element.textContent = t(element.dataset.i18n);
  });
  root.querySelectorAll('[data-i18n-placeholder]').forEach((element) => {
    element.placeholder = t(element.dataset.i18nPlaceholder);
  });
  root.querySelectorAll('[data-i18n-title]').forEach((element) => {
    element.title = t(element.dataset.i18nTitle);
  });
  root.querySelectorAll('[data-lang]').forEach((button) => {
    button.classList.toggle('is-active', button.dataset.lang === current);
    button.setAttribute('aria-pressed', String(button.dataset.lang === current));
  });
}

/** Switch the language, remember it, and let the screens redraw. */
export function setLanguage(language) {
  if (!LANGUAGES.includes(language)) return;
  current = language;
  try {
    localStorage.setItem(STORAGE_KEY, language);
  } catch {
    // A browser without storage still switches for this page view.
  }
  document.documentElement.lang = language;
  applyTranslations();
  document.dispatchEvent(new CustomEvent('languagechange', { detail: { language } }));
}

/** Apply the remembered language at start-up and wire the switch buttons. */
export function initLanguage() {
  current = readStored() ?? DEFAULT_LANGUAGE;
  document.documentElement.lang = current;
  applyTranslations();
  document.querySelectorAll('[data-lang]').forEach((button) => {
    button.addEventListener('click', () => setLanguage(button.dataset.lang));
  });
}

/** Seconds as "35 min 12 s", or a dash when nothing was recorded. */
export function formatDuration(seconds) {
  const total = Math.max(0, Math.round(Number(seconds) || 0));
  if (!total) return t('time_none');
  const m = Math.floor(total / 60);
  const s = total % 60;
  if (!m) return t('time_seconds', { s });
  return s ? t('time_minutes_seconds', { m, s }) : t('time_minutes', { m });
}
