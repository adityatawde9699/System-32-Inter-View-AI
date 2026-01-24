/**
 * InterView AI - Main Application JavaScript
 * * Handles:
 * - File upload and resume parsing
 * - Interview session management
 * - API communication
 * - UI state management
 */

// =============================================================================
// Configuration
// =============================================================================

const API_BASE = '/api';

// =============================================================================
// State
// =============================================================================

const state = {
    sessionId: null,
    resumeText: '',
    jobDescription: '',
    currentQuestion: '',
    questionNumber: 0,
    isInterviewActive: false,
    isRecording: false,
};

// Audio Recording State
let mediaRecorder = null;
let audioSocket = null;
let audioChunks = [];

// =============================================================================
// DOM Elements
// =============================================================================

const elements = {
    // Panels
    setupPanel: document.getElementById('setup-panel'),
    interviewPanel: document.getElementById('interview-panel'),
    summaryPanel: document.getElementById('summary-panel'),
    historyPanel: document.getElementById('history-panel'),

    // Nav
    navInterview: document.getElementById('nav-interview'),
    navHistory: document.getElementById('nav-history'),

    // Setup
    resumeDropzone: document.getElementById('resume-dropzone'),
    resumeInput: document.getElementById('resume-input'),
    resumeStatus: document.getElementById('resume-status'),
    jobDescription: document.getElementById('job-description'),
    startBtn: document.getElementById('start-btn'),

    // Interview
    alertBanner: document.getElementById('alert-banner'),
    alertText: document.getElementById('alert-text'),
    questionNumber: document.getElementById('question-number'),
    questionText: document.getElementById('question-text'),
    answerInput: document.getElementById('answer-input'),
    submitAnswerBtn: document.getElementById('submit-answer-btn'),
    nextQuestionBtn: document.getElementById('next-question-btn'),
    endSessionBtn: document.getElementById('end-session-btn'),

    // Metrics
    metricWpm: document.getElementById('metric-wpm'),
    wpmEstimated: document.getElementById('wpm-estimated'),
    metricFillers: document.getElementById('metric-fillers'),
    metricQuestions: document.getElementById('metric-questions'),
    metricScore: document.getElementById('metric-score'),

    // Evaluation
    evaluationCard: document.getElementById('evaluation-card'),
    evalTechnical: document.getElementById('eval-technical'),
    evalClarity: document.getElementById('eval-clarity'),
    evalDepth: document.getElementById('eval-depth'),
    evalComplete: document.getElementById('eval-complete'),
    evalFeedback: document.getElementById('eval-feedback'),

    // Summary
    summaryDuration: document.getElementById('summary-duration'),
    summaryQuestions: document.getElementById('summary-questions'),
    summaryScore: document.getElementById('summary-score'),
    summaryWpm: document.getElementById('summary-wpm'),
    summaryFillers: document.getElementById('summary-fillers'),
    downloadBtn: document.getElementById('download-btn'),
    restartBtn: document.getElementById('restart-btn'),

    // Audio Recording
    recordBtn: document.getElementById('record-btn'),
    volumeMeter: document.getElementById('volume-meter'),
    recordingStatus: document.getElementById('recording-status'),

    // Loading
    loadingOverlay: document.getElementById('loading-overlay'),
    loadingText: document.getElementById('loading-text'),

    // History
    historyList: document.getElementById('history-list'),
    historyEmpty: document.getElementById('history-empty'),
    historyStartBtn: document.getElementById('history-start-btn'),
};

// =============================================================================
// Utility Functions
// =============================================================================

function showLoading(message = 'Processing...') {
    elements.loadingText.textContent = message;
    elements.loadingOverlay.classList.remove('hidden');
}

function hideLoading() {
    elements.loadingOverlay.classList.add('hidden');
}

function showPanel(panel) {
    elements.setupPanel.classList.add('hidden');
    elements.interviewPanel.classList.add('hidden');
    elements.summaryPanel.classList.add('hidden');
    elements.historyPanel.classList.add('hidden');

    // Update Nav Active State
    if (elements.navInterview) elements.navInterview.classList.remove('active');
    if (elements.navHistory) elements.navHistory.classList.remove('active');

    if (panel === elements.historyPanel) {
        if (elements.navHistory) elements.navHistory.classList.add('active');
    } else if (panel !== elements.setupPanel && panel !== elements.interviewPanel && panel !== elements.summaryPanel) {
        // Generic fallback or custom logic
    } else {
        if (elements.navInterview) elements.navInterview.classList.add('active');
    }

    panel.classList.remove('hidden');
}

function showAlert(message, level = 'ok') {
    elements.alertText.textContent = message;
    elements.alertBanner.className = `alert-banner ${level}`;
    elements.alertBanner.classList.remove('hidden');
}

function hideAlert() {
    elements.alertBanner.classList.add('hidden');
}

function updateStartButton() {
    const canStart = state.resumeText.length > 50 &&
        elements.jobDescription.value.trim().length > 20;
    elements.startBtn.disabled = !canStart;
}

async function apiCall(endpoint, options = {}) {
    const response = await fetch(`${API_BASE}${endpoint}`, {
        headers: {
            'Content-Type': 'application/json',
        },
        ...options,
    });

    if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'API request failed');
    }

    return response.json();
}

// =============================================================================
// Audio Recording Functions
// =============================================================================

async function startRecording() {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        mediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm' });
        audioChunks = [];

        // Connect WebSocket for real-time coaching
        const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        audioSocket = new WebSocket(`${wsProtocol}//${window.location.host}/api/ws/audio/${state.sessionId}`);

        audioSocket.onopen = () => {
            console.log('🎤 Audio WebSocket connected');
        };

        audioSocket.onmessage = (event) => {
            const data = JSON.parse(event.data);
            if (data.type === 'coaching') {
                updateCoachingHud(data);
            }
        };

        audioSocket.onerror = (error) => {
            console.error('WebSocket error:', error);
        };

        audioSocket.onclose = () => {
            console.log('🎤 Audio WebSocket disconnected');
        };

        mediaRecorder.ondataavailable = (event) => {
            if (event.data.size > 0) {
                audioChunks.push(event.data);
                if (audioSocket && audioSocket.readyState === WebSocket.OPEN) {
                    audioSocket.send(event.data);
                }
            }
        };

        mediaRecorder.start(250); // Send chunks every 250ms
        state.isRecording = true;
        updateRecordingUI(true);

    } catch (error) {
        console.error('Failed to start recording:', error);
        alert('Microphone access is required for voice input. Please allow microphone access and try again.');
    }
}

async function stopRecording() {
    return new Promise((resolve) => {
        if (!mediaRecorder || mediaRecorder.state === 'inactive') {
            resolve();
            return;
        }

        // Set up onstop handler before calling stop
        mediaRecorder.onstop = async () => {
            // Stop all tracks
            mediaRecorder.stream.getTracks().forEach(track => track.stop());

            // Close WebSocket
            if (audioSocket) {
                audioSocket.close();
                audioSocket = null;
            }

            state.isRecording = false;
            updateRecordingUI(false);

            // Combine all chunks into a single blob
            if (audioChunks.length > 0) {
                const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
                console.log(`🎤 Recording complete: ${audioBlob.size} bytes`);

                // Submit for transcription
                await submitAudioForTranscription(audioBlob);
            }

            audioChunks = [];
            resolve();
        };

        mediaRecorder.stop();
    });
}

async function submitAudioForTranscription(audioBlob) {
    showLoading('Transcribing and evaluating...');

    try {
        const formData = new FormData();
        formData.append('audio', audioBlob, 'recording.webm');

        const response = await fetch(
            `${API_BASE}/answer/audio?session_id=${state.sessionId}`,
            {
                method: 'POST',
                body: formData,
            }
        );

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to process audio');
        }

        const result = await response.json();

        // Display transcript in the text area
        elements.answerInput.value = result.transcript;

        // Update coaching metrics
        const coaching = result.coaching;
        elements.metricWpm.textContent = Math.round(coaching.words_per_minute);
        elements.metricFillers.textContent = coaching.filler_count;

        // Hide estimated badge - audio-based WPM is real measurement
        if (elements.wpmEstimated) {
            elements.wpmEstimated.classList.add('hidden');
        }

        // Show coaching alert
        if (coaching.alert_level === 'warning') {
            showAlert(coaching.primary_alert, 'warning');
        } else {
            showAlert(coaching.primary_alert || '✅ Great delivery!', 'ok');
        }

        // Show evaluation
        const evaluation = result.evaluation;
        elements.evalTechnical.textContent = evaluation.technical_accuracy;
        elements.evalClarity.textContent = evaluation.clarity;
        elements.evalDepth.textContent = evaluation.depth;
        elements.evalComplete.textContent = evaluation.completeness;
        elements.metricScore.textContent = evaluation.average_score.toFixed(1);

        // Show feedback
        let feedbackHtml = '';
        if (evaluation.positive_note) {
            feedbackHtml += `👍 <strong>Strength:</strong> ${evaluation.positive_note}<br>`;
        }
        if (evaluation.improvement_tip) {
            feedbackHtml += `💡 <strong>Tip:</strong> ${evaluation.improvement_tip}`;
        }
        elements.evalFeedback.innerHTML = feedbackHtml;

        elements.evaluationCard.classList.remove('hidden');
        elements.submitAnswerBtn.disabled = true;
        elements.nextQuestionBtn.disabled = false;

        console.log('✅ Audio transcription complete:', result.transcript.substring(0, 50) + '...');

    } catch (error) {
        console.error('Audio transcription error:', error);
        showAlert(`❌ ${error.message}`, 'warning');
    } finally {
        hideLoading();
    }
}

function toggleRecording() {
    if (state.isRecording) {
        stopRecording();  // Now async but we don't await here
    } else {
        startRecording();
    }
}

function updateCoachingHud(data) {
    // Update volume meter
    if (elements.volumeMeter) {
        const volumeLevel = Math.min(data.volume_level * 10, 1);
        elements.volumeMeter.style.width = `${volumeLevel * 100}%`;

        // Change color based on speaking status
        if (data.is_speaking) {
            elements.volumeMeter.style.background = 'linear-gradient(90deg, #10b981, #22c55e)';
        } else {
            elements.volumeMeter.style.background = 'linear-gradient(90deg, #6b7280, #9ca3af)';
        }
    }

    // Show alert if not speaking loudly enough
    if (data.volume_alert && data.volume_alert !== 'OK') {
        showAlert(data.volume_alert, 'warning');
    }
}

function updateRecordingUI(isRecording) {
    if (elements.recordBtn) {
        if (isRecording) {
            elements.recordBtn.textContent = '⏹️ Stop Recording';
            elements.recordBtn.classList.add('recording');
        } else {
            elements.recordBtn.textContent = '🎤 Start Recording';
            elements.recordBtn.classList.remove('recording');
        }
    }

    if (elements.recordingStatus) {
        elements.recordingStatus.textContent = isRecording ? '● Recording...' : '';
        elements.recordingStatus.style.color = isRecording ? '#ef4444' : '';
    }
}

// =============================================================================
// File Upload Handling
// =============================================================================

function setupFileUpload() {
    const dropzone = elements.resumeDropzone;
    const input = elements.resumeInput;

    // Click to upload
    dropzone.addEventListener('click', () => input.click());

    // File selected
    input.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            handleFileUpload(e.target.files[0]);
        }
    });

    // Drag and drop
    dropzone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropzone.classList.add('dragover');
    });

    dropzone.addEventListener('dragleave', () => {
        dropzone.classList.remove('dragover');
    });

    dropzone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropzone.classList.remove('dragover');

        if (e.dataTransfer.files.length > 0) {
            handleFileUpload(e.dataTransfer.files[0]);
        }
    });
}

async function handleFileUpload(file) {
    if (!file.name.toLowerCase().endsWith('.pdf')) {
        showStatus('error', 'Please upload a PDF file');
        return;
    }

    showLoading('Parsing resume...');

    try {
        const formData = new FormData();
        formData.append('file', file);

        const response = await fetch(`${API_BASE}/upload/resume`, {
            method: 'POST',
            body: formData,
        });

        if (!response.ok) {
            throw new Error('Failed to parse resume');
        }

        const data = await response.json();
        state.resumeText = data.text_content;

        showStatus('success', `✅ Resume loaded: ${data.text_length} characters`);
        updateStartButton();

    } catch (error) {
        console.error('Upload error:', error);
        showStatus('error', `❌ ${error.message}`);
    } finally {
        hideLoading();
    }
}

function showStatus(type, message) {
    elements.resumeStatus.textContent = message;
    elements.resumeStatus.className = `status-message ${type}`;
    elements.resumeStatus.classList.remove('hidden');
}

// =============================================================================
// Interview Session Management
// =============================================================================

async function startSession() {
    showLoading('Starting interview...');

    try {
        const response = await apiCall('/session/start', {
            method: 'POST',
            body: JSON.stringify({
                resume_text: state.resumeText,
                job_description: elements.jobDescription.value.trim(),
            }),
        });

        state.sessionId = response.session_id;
        state.isInterviewActive = true;
        console.log('🎤 Session started with ID:', state.sessionId);

        // Get first question
        await getNextQuestion();

        showPanel(elements.interviewPanel);
        showAlert('✅ Interview started. Good luck!', 'ok');

    } catch (error) {
        console.error('Start session error:', error);
        alert(`Failed to start interview: ${error.message}`);
    } finally {
        hideLoading();
    }
}

async function getNextQuestion() {
    showLoading('Generating question...');
    hideAlert();

    console.log('📝 Getting next question for session:', state.sessionId);

    try {
        const response = await apiCall(`/question/next?session_id=${state.sessionId}`);

        state.currentQuestion = response.question_text;
        state.questionNumber = response.question_number;

        elements.questionNumber.textContent = state.questionNumber;
        elements.questionText.textContent = state.currentQuestion;
        elements.metricQuestions.textContent = state.questionNumber;

        // Reset answer area
        elements.answerInput.value = '';
        elements.answerInput.focus();
        elements.submitAnswerBtn.disabled = false;
        elements.nextQuestionBtn.disabled = true;
        elements.evaluationCard.classList.add('hidden');

    } catch (error) {
        console.error('Get question error:', error);
        alert(`Failed to get question: ${error.message}`);
    } finally {
        hideLoading();
    }
}

async function submitAnswer() {
    const answerText = elements.answerInput.value.trim();

    if (!answerText) {
        alert('Please enter your answer first');
        return;
    }

    showLoading('Evaluating your answer...');

    try {
        // Estimate duration based on word count
        const wordCount = answerText.split(/\s+/).length;
        const duration = wordCount / 2.5; // ~150 WPM estimate

        const response = await apiCall('/answer/submit', {
            method: 'POST',
            body: JSON.stringify({
                session_id: state.sessionId,
                answer_text: answerText,
                duration_seconds: duration,
            }),
        });

        // Update coaching metrics
        const coaching = response.coaching;
        elements.metricWpm.textContent = Math.round(coaching.words_per_minute);
        elements.metricFillers.textContent = coaching.filler_count;

        // Show estimated badge - text-based WPM is an estimate
        if (elements.wpmEstimated) {
            elements.wpmEstimated.classList.remove('hidden');
        }

        // Show coaching alert
        if (coaching.alert_level === 'warning') {
            showAlert(coaching.primary_alert, 'warning');
        } else {
            showAlert(coaching.primary_alert, 'ok');
        }

        // Show evaluation
        const evaluation = response.evaluation;
        elements.evalTechnical.textContent = evaluation.technical_accuracy;
        elements.evalClarity.textContent = evaluation.clarity;
        elements.evalDepth.textContent = evaluation.depth;
        elements.evalComplete.textContent = evaluation.completeness;
        elements.metricScore.textContent = evaluation.average_score.toFixed(1);

        // Show feedback
        let feedbackHtml = '';
        if (evaluation.positive_note) {
            feedbackHtml += `👍 <strong>Strength:</strong> ${evaluation.positive_note}<br>`;
        }
        if (evaluation.improvement_tip) {
            feedbackHtml += `💡 <strong>Tip:</strong> ${evaluation.improvement_tip}`;
        }
        elements.evalFeedback.innerHTML = feedbackHtml;

        elements.evaluationCard.classList.remove('hidden');
        elements.submitAnswerBtn.disabled = true;
        elements.nextQuestionBtn.disabled = false;

    } catch (error) {
        console.error('Submit answer error:', error);
        alert(`Failed to process answer: ${error.message}`);
    } finally {
        hideLoading();
    }
}

async function endSession() {
    showLoading('Ending session...');

    try {
        // Securely get the current user's token
        const user = firebase.auth().currentUser;
        let headers = {
            'Content-Type': 'application/json'
        };

        if (user) {
            const token = await user.getIdToken();
            headers['Authorization'] = `Bearer ${token}`;
            console.log('🔐 Sending request with Auth Token');
        } else {
            console.log('⚠️ No user logged in (Guest Mode)');
        }

        // Send request to end session
        const response = await fetch(`${API_BASE}/session/end?session_id=${state.sessionId}`, {
            method: 'POST',
            headers: headers
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to end session');
        }

        const data = await response.json();

        // Update UI with Summary
        elements.summaryDuration.textContent = data.duration_minutes.toFixed(1);
        elements.summaryQuestions.textContent = data.questions_asked;
        elements.summaryScore.textContent = data.average_score.toFixed(1);
        elements.summaryWpm.textContent = Math.round(data.average_wpm);
        elements.summaryFillers.textContent = data.total_fillers;

        state.isInterviewActive = false;
        showPanel(elements.summaryPanel);

        let msg = 'Interview ended!';
        if (user) {
            msg += ` Report sent to ${user.email}`;
            // Also save to Firestore for history
            await saveInterviewReport(data);
        }
        showAlert(msg, 'ok');

    } catch (error) {
        console.error('End session error:', error);
        alert(`Failed to end session: ${error.message}`);
    } finally {
        hideLoading();
    }
}

function downloadReport() {
    if (!state.sessionId) return;
    // Direct link trigger for file download
    window.location.href = `${API_BASE}/session/report/${state.sessionId}/download`;
}

async function saveInterviewReport(summaryData) {
    const user = firebase.auth().currentUser;
    if (!user) {
        console.warn('⚠️ No user logged in. Report not saved to Firebase.');
        return;
    }

    try {
        console.log('📤 Saving interview report to Firestore...');

        const reportData = {
            userId: user.uid,
            userEmail: user.email,
            timestamp: firebase.firestore.FieldValue.serverTimestamp(),
            sessionId: state.sessionId,
            metrics: {
                durationMinutes: summaryData.duration_minutes,
                questionsAsked: summaryData.questions_asked,
                averageScore: summaryData.average_score,
                averageWpm: summaryData.average_wpm,
                totalFillers: summaryData.total_fillers
            },
            jobDescription: elements.jobDescription.value.trim(),
        };

        if (state.resumeText) {
            reportData.resumeSnippet = state.resumeText.substring(0, 500);
        }

        await db.collection('reports').add(reportData);
        console.log('✅ Interview report successfully saved to Firestore');

    } catch (error) {
        console.error('❌ Error saving report to Firestore:', error);
    }
}

async function loadInterviewHistory() {
    const user = firebase.auth().currentUser;
    if (!user) return;

    elements.historyList.innerHTML = `
        <div class="loading-placeholder">
            <div class="spinner-small"></div>
            <p>Loading your history...</p>
        </div>
    `;
    elements.historyEmpty.classList.add('hidden');
    elements.historyList.classList.remove('hidden');

    try {
        const snapshot = await db.collection('reports')
            .where('userId', '==', user.uid)
            .orderBy('timestamp', 'desc')
            .limit(20)
            .get();

        if (snapshot.empty) {
            elements.historyList.classList.add('hidden');
            elements.historyEmpty.classList.remove('hidden');
            return;
        }

        const reports = [];
        snapshot.forEach(doc => {
            reports.push({ id: doc.id, ...doc.data() });
        });

        renderHistoryList(reports);

    } catch (error) {
        console.error('Error loading history:', error);
        elements.historyList.innerHTML = `<p class="error">Failed to load history: ${error.message}</p>`;
    }
}

function renderHistoryList(reports) {
    elements.historyList.innerHTML = '';

    reports.forEach(report => {
        const date = report.timestamp ? report.timestamp.toDate() : new Date();
        const day = date.getDate();
        const month = date.toLocaleString('default', { month: 'short' });

        const card = document.createElement('div');
        card.className = 'history-card';
        card.innerHTML = `
            <div class="history-date">
                <span class="date-day">${day}</span>
                <span class="date-month">${month}</span>
            </div>
            <div class="history-info">
                <div class="history-title">Interview Session</div>
                <div class="history-meta">
                    <span class="history-meta-item">⏱️ ${report.metrics.durationMinutes.toFixed(1)}m</span>
                    <span class="history-meta-item">❓ ${report.metrics.questionsAsked} Questions</span>
                </div>
            </div>
            <div class="history-score">
                <div class="score-value">${report.metrics.averageScore.toFixed(1)}</div>
                <div class="score-label">Avg Score</div>
            </div>
        `;

        // Add click listener to show summary (re-using existing summary UI)
        card.addEventListener('click', () => {
            elements.summaryDuration.textContent = report.metrics.durationMinutes.toFixed(1);
            elements.summaryQuestions.textContent = report.metrics.questionsAsked;
            elements.summaryScore.textContent = report.metrics.averageScore.toFixed(1);
            elements.summaryWpm.textContent = Math.round(report.metrics.averageWpm);
            elements.summaryFillers.textContent = report.metrics.totalFillers;

            showPanel(elements.summaryPanel);
        });

        elements.historyList.appendChild(card);
    });
}

function restartInterview() {
    // Reset state
    state.sessionId = null;
    state.resumeText = '';
    state.jobDescription = '';
    state.currentQuestion = '';
    state.questionNumber = 0;
    state.isInterviewActive = false;

    // Reset UI
    elements.resumeInput.value = '';
    elements.resumeStatus.classList.add('hidden');
    elements.jobDescription.value = '';
    elements.startBtn.disabled = true;
    elements.metricWpm.textContent = '0';
    elements.metricFillers.textContent = '0';
    elements.metricQuestions.textContent = '0';
    elements.metricScore.textContent = '0.0';

    showPanel(elements.setupPanel);
}

// =============================================================================
// Event Listeners
// =============================================================================

function setupEventListeners() {
    // Setup panel
    elements.jobDescription.addEventListener('input', updateStartButton);
    elements.startBtn.addEventListener('click', startSession);

    // Interview panel
    elements.submitAnswerBtn.addEventListener('click', submitAnswer);
    elements.nextQuestionBtn.addEventListener('click', getNextQuestion);
    elements.endSessionBtn.addEventListener('click', endSession);
    if (elements.downloadBtn) {
        elements.downloadBtn.addEventListener('click', downloadReport);
    }

    // Allow Ctrl+Enter to submit answer
    elements.answerInput.addEventListener('keydown', (e) => {
        if (e.ctrlKey && e.key === 'Enter' && !elements.submitAnswerBtn.disabled) {
            submitAnswer();
        }
    });

    // Audio recording
    if (elements.recordBtn) {
        elements.recordBtn.addEventListener('click', toggleRecording);
    }

    // Summary panel
    elements.restartBtn.addEventListener('click', restartInterview);

    // Navigation
    if (elements.navInterview) {
        elements.navInterview.addEventListener('click', (e) => {
            e.preventDefault();
            if (state.isInterviewActive) {
                showPanel(elements.interviewPanel);
            } else if (state.sessionId && !elements.summaryPanel.classList.contains('hidden')) {
                showPanel(elements.summaryPanel);
            } else {
                showPanel(elements.setupPanel);
            }
        });
    }

    if (elements.navHistory) {
        elements.navHistory.addEventListener('click', (e) => {
            e.preventDefault();
            loadInterviewHistory();
            showPanel(elements.historyPanel);
        });
    }

    if (elements.historyStartBtn) {
        elements.historyStartBtn.addEventListener('click', () => {
            showPanel(elements.setupPanel);
        });
    }
}

// =============================================================================
// Initialization
// =============================================================================

document.addEventListener('DOMContentLoaded', () => {
    console.log('🎙️ InterView AI initialized');

    setupFileUpload();
    setupEventListeners();

    // Focus on job description if no resume yet
    elements.jobDescription.focus();
});