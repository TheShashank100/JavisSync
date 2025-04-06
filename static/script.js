document.addEventListener('DOMContentLoaded', () => {
    // Audio components
    const synth = new Tone.Synth({
        oscillator: {
            type: 'sine'
        },
        envelope: {
            attack: 0.005,
            decay: 0.1,
            sustain: 0.3,
            release: 1
        }
    }).toDestination();

    const drumSampler = new Tone.Sampler({
        urls: {
            C1: "kick.wav",
            D1: "snare.wav",
            E1: "hihat.wav",
            F1: "clap.wav"
        },
        release: 1,
        baseUrl: "/static/sounds/"
    }).toDestination();

    // UI elements
    const responseBox = document.getElementById('response-box');
    const userInput = document.getElementById('user-input');
    const sendBtn = document.getElementById('send-btn');
    const singBtn = document.getElementById('sing-btn');
    const visualizer = document.getElementById('visualizer');
    const moodDisplay = document.getElementById('mood-display');
    let currentSession = null;
    let isPlaying = false;
    let currentLoop = null;

    // Initialize audio context on first interaction
    document.addEventListener('click', async function initAudio() {
        try {
            await Tone.start();
            console.log('Audio is ready');
            document.removeEventListener('click', initAudio);
            
            // Warm up the synths
            synth.triggerAttackRelease("C4", "8n");
            drumSampler.triggerAttackRelease("C1", "8n");
        } catch (e) {
            console.error('Audio initialization failed', e);
        }
    }, { once: true });

    // Add message to chat
    function addMessage(text, sender, hasPlayButton = false) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${sender}`;
        
        if (hasPlayButton) {
            messageDiv.innerHTML = `
                <div class="message-content">${text}</div>
                <button class="play-btn">${isPlaying ? '⏹ Stop' : '▶ Play'}</button>
            `;
            const playBtn = messageDiv.querySelector('.play-btn');
            playBtn.addEventListener('click', () => {
                if (isPlaying) {
                    stopPlayback();
                    playBtn.textContent = '▶ Play';
                } else {
                    playMusic();
                    playBtn.textContent = '⏹ Stop';
                }
            });
        } else {
            messageDiv.innerHTML = `<div class="message-content">${text}</div>`;
        }
        
        responseBox.appendChild(messageDiv);
        responseBox.scrollTop = responseBox.scrollHeight;
    }

    // Send message to server
    async function sendMessage() {
        const text = userInput.value.trim();
        if (!text) return;

        addMessage(text, 'user');
        userInput.value = '';
        
        try {
            const response = await fetch('/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ prompt: text })
            });

            if (!response.ok) {
                const errorText = await response.text();
                throw new Error(errorText || 'Server error');
            }

            const data = await response.json();
            if (!data.lyrics || !data.session_id) {
                throw new Error('Invalid response format');
            }

            currentSession = data.session_id;
            addMessage(data.lyrics, 'bot', true);
            
        } catch (error) {
            console.error("Error:", error);
            addMessage(`Error: ${error.message}`, 'error');
        }
    }

    // Play generated music
    async function playMusic() {
        if (isPlaying) return;
        if (!currentSession) {
            addMessage("Generate lyrics first", 'error');
            return;
        }

        try {
            const response = await fetch(`/music/${currentSession}`);
            if (!response.ok) {
                throw new Error(await response.text());
            }

            const musicData = await response.json();
            if (!musicData.beats || !musicData.tempo) {
                throw new Error('Invalid music data');
            }

            // Stop any existing playback
            if (currentLoop) currentLoop.dispose();
            
            // Set tempo
            Tone.Transport.bpm.value = musicData.tempo;
            
            // Schedule melody
            const now = Tone.now();
            musicData.beats.forEach((beat, i) => {
                const note = i % 2 === 0 ? 'C4' : 'Eb4';
                synth.triggerAttackRelease(
                    note, 
                    '8n', 
                    now + (beat.time * 0.5),
                    Math.random() * 0.5 + 0.5
                );
            });

            // Schedule drums
            currentLoop = new Tone.Loop(time => {
                // Kick on quarter notes
                drumSampler.triggerAttackRelease("C1", "8n", time);
                
                // Snare on off-beats
                if (Math.floor(time * 2) % 2 === 1) {
                    drumSampler.triggerAttackRelease("D1", "16n", time);
                }
                
                // Hi-hats
                drumSampler.triggerAttackRelease("E1", "16n", time + 0.25);
            }, "1n").start(0);

            // Start transport
            Tone.Transport.start();
            isPlaying = true;
            
            // Auto-stop after 32 beats
            Tone.Transport.scheduleOnce(() => {
                stopPlayback();
                document.querySelectorAll('.play-btn').forEach(btn => {
                    btn.textContent = '▶ Play';
                });
            }, "32n");

        } catch (error) {
            console.error("Playback error:", error);
            addMessage(`Playback error: ${error.message}`, 'error');
            isPlaying = false;
        }
    }

    // Stop playback
    function stopPlayback() {
        Tone.Transport.stop();
        Tone.Transport.cancel();
        if (currentLoop) {
            currentLoop.dispose();
            currentLoop = null;
        }
        isPlaying = false;
    }


    // Create visualizer bars
    function createVisualizer() {
        visualizer.innerHTML = '';
        for (let i = 0; i < 32; i++) {
            const bar = document.createElement('div');
            bar.className = 'visualizer-bar';
            visualizer.appendChild(bar);
        }
    }

    // Update visualizer based on playback
    function updateVisualizer(beatIndex) {
        const bars = document.querySelectorAll('.visualizer-bar');
        bars.forEach((bar, i) => {
            if (i === beatIndex % 32) {
                bar.style.height = `${Math.random() * 80 + 20}%`;
                bar.style.backgroundColor = `hsl(${Math.random() * 60 + 200}, 80%, 60%)`;
            } else {
                bar.style.height = '10%';
            }
        });
    }

    // Event listeners
    sendBtn.addEventListener('click', sendMessage);
    userInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });
    singBtn.addEventListener('click', () => {
        if (isPlaying) {
            stopPlayback();
            document.querySelectorAll('.play-btn').forEach(btn => {
                btn.textContent = '▶ Play';
            });
        } else {
            createVisualizer();
            playMusic();
            document.querySelectorAll('.play-btn').forEach(btn => {
                btn.textContent = '⏹ Stop';
            });
        }
    });

    // Enhanced music generation
    function generateMusicPattern(mood) {
        const patterns = {
            happy: {
                chords: ['C4', 'G4', 'A4', 'F4'],
                rhythm: [1, 0, 1, 0, 1, 1, 0, 1]
            },
            sad: {
                chords: ['Am', 'F', 'C', 'G'],
                rhythm: [1, 0, 0, 0, 1, 0, 0, 0]
            },
            angry: {
                chords: ['Dm', 'A#', 'F', 'C'],
                rhythm: [1, 1, 1, 1, 1, 1, 1, 1]
            },
            chill: {
                chords: ['Cmaj7', 'Dm7', 'Em7', 'Am7'],
                rhythm: [1, 0, 0, 1, 0, 0, 1, 0]
            }
        };
        return patterns[mood] || patterns.happy;
    }

    // Handle window close
    window.addEventListener('beforeunload', () => {
        stopPlayback();
        Tone.context.close();
    });

    // Initialize visualizer
    createVisualizer();
});
