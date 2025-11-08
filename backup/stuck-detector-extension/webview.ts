// This file exports a function that returns the HTML content for the webview.
// This version uses the v9 Modular Firebase SDK AND adds a pie chart.

export function getWebviewContent(firebaseConfig: object, studentFilter?: string): string {
  // We need to stringify the config to inject it into the HTML script
  const configString = JSON.stringify(firebaseConfig);
  const isStudentView = !!studentFilter;
  const isProfessorView = !isStudentView;

  return `<!DOCTYPE html>
  <html lang="en">
  <head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Stuck Detector Dashboard</title>
    
    <!-- 1. Import Chart.js from a CDN -->
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    
    <!-- 2. Import Firebase v9+ (modular) SDKs from the CDN -->
    <script type="module">
      // Import v9 modular functions
      import { initializeApp } from "https://www.gstatic.com/firebasejs/9.6.1/firebase-app.js";
      import { getFirestore, collection, onSnapshot } from "https://www.gstatic.com/firebasejs/9.6.1/firebase-firestore.js";

      // 3. Initialize Firebase IN THE WEBVIEW
      const firebaseConfig = ${configString};
      const app = initializeApp(firebaseConfig);
      const db = getFirestore(app);

      // 4. Initialize Bar Chart (Topics)
      const barCtx = document.getElementById('topicChart').getContext('2d');
      const topicChart = new Chart(barCtx, {
        type: 'bar',
        data: {
          labels: [], // e.g., ['useState', 'fetch', 'Promise']
          datasets: [{
            label: 'Instances of Difficulty',
            data: [], // e.g., [5, 12, 3]
            backgroundColor: 'rgba(54, 162, 235, 0.6)',
            borderColor: 'rgba(54, 162, 235, 1)',
            borderWidth: 1
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          scales: {
            y: { beginAtZero: true, ticks: { color: '#CCC' }, grid: { color: 'rgba(255, 255, 255, 0.1)' }},
            x: { ticks: { color: '#CCC' }, grid: { color: 'rgba(255, 255, 255, 0.1)' }}
          },
          plugins: { legend: { labels: { color: '#CCC' }}}
        }
      });

      // 5. Initialize Pie Chart (Heuristics)
      const pieCtx = document.getElementById('heuristicChart').getContext('2d');
      const heuristicChart = new Chart(pieCtx, {
        type: 'pie',
        data: {
          labels: [], // e.g., ['churn', 'jitter', 'flip']
          datasets: [{
            label: 'Detection Methods',
            data: [], // e.g., [10, 4, 2]
            backgroundColor: [
              'rgba(255, 99, 132, 0.6)',
              'rgba(255, 206, 86, 0.6)',
              'rgba(75, 192, 192, 0.6)'
            ],
            borderColor: [
              'rgba(255, 99, 132, 1)',
              'rgba(255, 206, 86, 1)',
              'rgba(75, 192, 192, 1)'
            ],
            borderWidth: 1
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: { legend: { labels: { color: '#CCC' }}}
        }
      });


      // 6. Connect to Firestore and listen for real-time updates (v9 syntax)
      const stuckEventsRef = collection(db, "stuckEvents");
      
      onSnapshot(stuckEventsRef, (snapshot) => {
        console.log("Got new data from Firestore!");
        
        const topicCounts = {};
        const heuristicCounts = {};
        const isStudentView = ${isStudentView};
        const isProfessorView = ${isProfessorView};
        const studentFilter = "${studentFilter || ''}";
        const allStudents = new Set();
        
        // Get selected student filter for professor view
        let selectedStudent = 'all';
        if (isProfessorView) {
          const studentSelect = document.getElementById('studentSelect');
          selectedStudent = studentSelect ? studentSelect.value : 'all';
        }
        
        snapshot.docs.forEach((doc) => {
          const data = doc.data();
          
          // Collect all student IDs for professor dropdown
          if (isProfessorView && data.studentId) {
            allStudents.add(data.studentId);
          }
          
          // Filter data based on view type and selections
          if (isStudentView && data.studentId !== studentFilter) {
            return;
          }
          if (isProfessorView && selectedStudent !== 'all' && data.studentId !== selectedStudent) {
            return;
          }
          
          // Use smart categorization if available, fallback to original word
          const category = data.category || data.contextWord;
          if (category) {
            topicCounts[category] = (topicCounts[category] || 0) + 1;
          }

          // Aggregate Heuristic data (for pie chart)
          const heuristic = data.heuristic;
          if (heuristic) {
            heuristicCounts[heuristic] = (heuristicCounts[heuristic] || 0) + 1;
          }
        });
        
        // Update professor dropdown with students
        if (isProfessorView) {
          const studentSelect = document.getElementById('studentSelect');
          if (studentSelect) {
            const currentValue = studentSelect.value;
            studentSelect.innerHTML = '<option value="all">All Students</option>';
            Array.from(allStudents).sort().forEach(studentId => {
              const option = document.createElement('option');
              option.value = studentId;
              option.textContent = studentId;
              if (studentId === currentValue) option.selected = true;
              studentSelect.appendChild(option);
            });
          }
        }

        // Update Bar Chart
        topicChart.data.labels = Object.keys(topicCounts);
        topicChart.data.datasets[0].data = Object.values(topicCounts);
        topicChart.update();

        // Update Pie Chart with friendly names
        const heuristicLabels = {
          'churn': '⚡ Rapid Typing',
          'cursor': '🔍 Line Jumping', 
          'file': '📁 File Switching',
          'idle': '🤔 Idle Staring'
        };
        
        const friendlyHeuristicLabels = Object.keys(heuristicCounts).map(
          key => heuristicLabels[key] || key
        );
        
        heuristicChart.data.labels = friendlyHeuristicLabels;
        heuristicChart.data.datasets[0].data = Object.values(heuristicCounts);
        heuristicChart.update();

      }, (error) => {
        console.error("Error listening to Firestore: ", error);
      });

      // Professor controls event listeners
      if (${isProfessorView}) {
        // Student filter dropdown
        const studentSelect = document.getElementById('studentSelect');
        if (studentSelect) {
          studentSelect.addEventListener('change', () => {
            // Trigger a re-render by calling onSnapshot again
            // The data will be filtered in the next update cycle
            console.log('Student filter changed to:', studentSelect.value);
          });
        }

        // Clear data button
        const clearButton = document.getElementById('clearDataButton');
        if (clearButton) {
          clearButton.addEventListener('click', () => {
            const confirmed = confirm('Are you sure you want to clear ALL student analytics data? This cannot be undone.');
            if (confirmed) {
              // Send message to extension
              const vscode = acquireVsCodeApi();
              vscode.postMessage({ command: 'clearData' });
            }
          });
        }
      }

    </script>
  </head>
  <body>
    <h1>${isStudentView ? `📈 My Learning Analytics - ${studentFilter}` : '🤖 AI TA - Class Analytics Dashboard'}</h1>
    <p>${isStudentView ? 'Track your programming progress and see what concepts you\'ve worked on.' : 'Real-time analytics showing what programming concepts your students are struggling with.'}</p>
    
    ${isProfessorView ? `
    <!-- Professor Controls -->
    <div style="margin: 20px 0; padding: 15px; background: rgba(255,255,255,0.1); border-radius: 8px;">
      <label for="studentSelect" style="color: #FFF; margin-right: 10px;">Filter by Student:</label>
      <select id="studentSelect" style="margin-right: 20px; padding: 5px; background: #2d2d30; color: #CCC; border: 1px solid #555;">
        <option value="all">All Students</option>
      </select>
      <button id="clearDataButton" style="padding: 5px 15px; background: #c94824; color: white; border: none; border-radius: 4px; cursor: pointer;">
        🗑️ Clear All Data
      </button>
    </div>` : ''}
    
    <!-- Charts -->
    <div style="display: flex; width: 90vw; height: 60vh;">
      <div id="chartContainer" style="flex: 1; margin-right: 10px;">
        <h2>📊 Programming Concepts (Smart Categories)</h2>
        <canvas id="topicChart"></canvas>
      </div>
      <div id="chartContainer" style="flex: 1; margin-left: 10px;">
        <h2>🎯 Detection Methods</h2>
        <canvas id="heuristicChart"></canvas>
      </div>
    </div>

  </body>
  </html>`;
}