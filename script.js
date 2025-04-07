// Toggle sidebar collapse
function toggleSidebar() {
  const sidebar = document.querySelector('.sidebar');
  sidebar.classList.toggle('collapsed');
  
  // Save state to localStorage
  const isCollapsed = sidebar.classList.contains('collapsed');
  localStorage.setItem('sidebarCollapsed', isCollapsed);
}

// Toggle dark/light mode
function toggleTheme() {
  const body = document.body;
  body.classList.toggle('dark-mode');
  body.classList.toggle('light-mode');
  
  // Save theme preference
  const isDarkMode = body.classList.contains('dark-mode');
  localStorage.setItem('darkMode', isDarkMode);
}

// Initialize UI state
function initUI() {
  // Set sidebar state
  const sidebarCollapsed = localStorage.getItem('sidebarCollapsed') === 'true';
  if (sidebarCollapsed) {
    document.querySelector('.sidebar').classList.add('collapsed');
  }

  // Set theme
  const darkMode = localStorage.getItem('darkMode') !== 'false'; // Default to dark
  document.body.classList.toggle('dark-mode', darkMode);
  document.body.classList.toggle('light-mode', !darkMode);
}

// Chat functionality
document.addEventListener('DOMContentLoaded', () => {
  initUI();
  
  const responseBox = document.getElementById('response-box');
  const userInput = document.getElementById('user-input');
  const sendBtn = document.getElementById('send-btn');

  // Add message to chat
  function addMessage(text, sender) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${sender}`;
    messageDiv.textContent = text;
    responseBox.appendChild(messageDiv);
    responseBox.scrollTop = responseBox.scrollHeight;
  }

  // Send message to server
  async function sendMessage() {
    const text = userInput.value.trim();
    if (!text) return;

    sendBtn.disabled = true;
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
        throw new Error('Failed to get response');
      }

      const data = await response.json();
      if (!data.lyrics) {
        throw new Error('No lyrics received');
      }

      addMessage(data.lyrics, 'bot');
      
    } catch (error) {
      addMessage(`Error: ${error.message}`, 'error');
    } finally {
      sendBtn.disabled = false;
    }
  }

  // Event listeners
  sendBtn.addEventListener('click', sendMessage);
  userInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });
});