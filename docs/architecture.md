# DealWhisper Architecture

## System Architecture Diagram

```mermaid
graph TB
    subgraph USER["🎯 User Layer"]
        Browser["Browser<br/><i>React 19 + Vite</i>"]
        Mic["Microphone<br/><i>16kHz PCM Audio</i>"]
        Cam["Camera / Screen<br/><i>JPEG Frames</i>"]
    end

    subgraph FRONTEND["⚡ Frontend (React)"]
        PreCall["Pre-Call Setup<br/><i>Buyer context, research, briefing chat</i>"]
        LiveSession["Live Session<br/><i>WebSocket audio/video, HUD, whisper feed</i>"]
        PostCall["Post-Call Debrief<br/><i>AI follow-ups, coaching metrics</i>"]
    end

    subgraph BACKEND["🔧 Backend (FastAPI on Cloud Run)"]
        REST["REST API Endpoints<br/><i>/api/research, /api/briefing, /api/sessions</i>"]
        WS["WebSocket Gateway<br/><i>/ws/call/{session_id}</i>"]
        Artifacts["Session Artifact Store<br/><i>Summaries, transcripts, coaching</i>"]
        subgraph TOOLS["10 Function Tools"]
            T1["get_buyer_profile"]
            T2["get_company_intel"]
            T3["get_battle_card"]
            T4["get_case_studies"]
            T5["get_objection_handler"]
            T6["get_pricing_guidance"]
            T7["get_discovery_questions"]
            T8["get_product_specs"]
            T9["get_deal_history"]
            T10["get_closing_techniques"]
        end
    end

    subgraph GCP["☁️ Google Cloud"]
        GeminiLive["Vertex AI<br/><b>Gemini Live 2.5 Flash</b><br/><i>Real-time audio/video</i>"]
        GeminiFlash["Vertex AI<br/><b>Gemini 2.5 Flash</b><br/><i>Briefing chat, debrief</i>"]
        CloudRun["Cloud Run<br/><i>Hosting</i>"]
        CloudBuild["Cloud Build<br/><i>CI/CD</i>"]
        Firestore["Firestore (Optional)<br/><i>Buyer data, company intel</i>"]
    end

    %% User → Frontend
    Browser --> PreCall
    Browser --> LiveSession
    Browser --> PostCall
    Mic --> LiveSession
    Cam --> LiveSession

    %% Frontend → Backend
    PreCall -- "REST" --> REST
    LiveSession -- "WebSocket ↔" --> WS
    PostCall -- "REST" --> REST

    %% Backend → Google Cloud
    WS -- "Bidirectional Audio/Video ↔" --> GeminiLive
    REST -- "Briefing Chat" --> GeminiFlash
    WS --> Artifacts

    %% Gemini Tool Calls
    GeminiLive -- "Tool Calls" --> TOOLS
    TOOLS -- "Responses" --> GeminiLive

    %% Infrastructure
    CloudBuild --> CloudRun
    CloudRun --> BACKEND
    Firestore -.-> TOOLS

    %% Styling
    classDef userStyle fill:#2d2418,stroke:#d4a84b,stroke-width:2px,color:#d4a84b
    classDef frontendStyle fill:#0d2d2a,stroke:#14b8a6,stroke-width:2px,color:#14b8a6
    classDef backendStyle fill:#0d1b3d,stroke:#3b82f6,stroke-width:2px,color:#3b82f6
    classDef gcpStyle fill:#0d2d14,stroke:#22c55e,stroke-width:2px,color:#22c55e
    classDef toolStyle fill:#1a1040,stroke:#a78bfa,stroke-width:1px,color:#a78bfa

    class Browser,Mic,Cam userStyle
    class PreCall,LiveSession,PostCall frontendStyle
    class REST,WS,Artifacts backendStyle
    class GeminiLive,GeminiFlash,CloudRun,CloudBuild,Firestore gcpStyle
    class T1,T2,T3,T4,T5,T6,T7,T8,T9,T10 toolStyle
```

## Data Flow Summary

| Flow | Protocol | Path | Purpose |
|------|----------|------|---------|
| Live Audio/Video | WebSocket | Browser → FastAPI → Gemini Live 2.5 Flash | Real-time call coaching |
| Briefing Chat | REST/HTTP | Browser → FastAPI → Gemini 2.5 Flash | Pre-call preparation |
| Tool Calls | gRPC/HTTP | Gemini → FastAPI Tools → Gemini | Dynamic context retrieval |
| Artifacts | Internal | FastAPI → Artifact Store | Session persistence |

## Key Components

- **Gemini Live 2.5 Flash**: Powers real-time multimodal streaming (audio + video) during live sales calls
- **Gemini 2.5 Flash**: Handles pre-call briefing chat and post-call debrief generation
- **10 Function Tools**: Provide Gemini with real-time access to buyer profiles, battle cards, case studies, objection handlers, pricing guidance, and more
- **WebSocket Gateway**: Bidirectional relay between browser and Gemini Live API for low-latency streaming
- **Session Artifact Store**: Persists call summaries, transcripts, and coaching metrics
