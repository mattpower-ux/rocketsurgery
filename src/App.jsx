import './App.css'

function App() {
  return (
    <div className="app">

      <header className="topbar">
        <div className="logo">RocketSurgery</div>

        <button className="newJobButton">
          NEW JOB
        </button>
      </header>

      <main className="homeScreen">

        <h1>
          What do you need help installing?
        </h1>

        <input
          className="queryBox"
          type="text"
          placeholder="Ask a construction question..."
        />

        <button className="startButton">
          START WALKTHROUGH
        </button>

      </main>

    </div>
  )
}

export default App
