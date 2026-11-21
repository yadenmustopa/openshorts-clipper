# PRD + Execution Handover — OpenShorts Clipper

**Version:** 1.0  
**Date:** 2026-11-21  
**Status:** Approved direction; execute Phase 0 only in the first Claude Work run  
**Default repository name:** `openshorts-clipper`  
**Preferred repository:** a GitHub fork of `https://github.com/mutonby/openshorts` under the user's authenticated GitHub account  
**Secondary dependency:** `https://github.com/heygen-com/hyperframes`  
**Language:** User communication and documentation in Indonesian; code, schemas and identifiers in English.

---

## A. INSTRUKSI LANGSUNG UNTUK CLAUDE WORK

Anda bertindak sebagai **Principal Software Architect, Senior Full-Stack Engineer, DevOps Engineer, dan Autonomous Agent Engineer**. Tugasnya adalah menyiapkan fondasi dan kemudian mengembangkan sebuah **autonomous self-hosted video clipper** berbasis fork OpenShorts, dengan HyperFrames untuk komposisi visual, dan Codex/Claude Code sebagai AI orchestrator.

**Mulai sekarang dengan Phase 0 (repository + audit + baseline) saja.** Jangan menganggap seluruh roadmap telah diminta untuk diimplementasikan dalam satu eksekusi. Jangan membuat klaim sudah menjalankan tes lokal di PC user jika Anda hanya punya akses cloud. Kerjakan seluruh langkah yang aksesnya tersedia; untuk akses yang terblokir, berikan blocker spesifik dan langkah otorisasi pengguna. Jangan hanya mengembalikan rencana tanpa mencoba membuat repository jika GitHub tersedia.

Prioritas pertama:
1. Verifikasi repository sumber OpenShorts dan HyperFrames pada revisi terkini; catat commit SHA/tag yang diinspeksi.
2. Identifikasi akun/organisasi GitHub yang sedang diotorisasi. Buat fork bernama `openshorts-clipper` di akun itu bila diizinkan. **Fork dari repository publik akan bersifat publik; jangan berasumsi repo private.** Jika akun belum terhubung, minta koneksi/otorisasi yang diperlukan. Jangan memilih owner berdasarkan dugaan.
3. Jika fork tidak dimungkinkan, laporkan alasan dan tawarkan fallback repository baru dengan `upstream` remote yang menunjuk ke OpenShorts; *jangan* beralih tanpa menjelaskan trade-off atribusi dan hubungan fork.
4. Tetapkan `origin` ke repo pengguna dan `upstream` ke `https://github.com/mutonby/openshorts.git`. Catat branch utama/commit baseline.
5. Buat branch `chore/phase-0-foundation` (jangan commit pekerjaan langsung ke branch utama) dan susun audit awal, dokumentasi, aturan agent, serta pengujian smoke minimal tanpa merusak aplikasi asal.
6. Buat Pull Request Phase 0 bila hak akses memungkinkan. Jika tidak, push branch lalu berikan URL/commit SHA yang sebenarnya.
7. Laporkan dengan jelas mana yang sudah dilakukan, belum dilakukan, tervalidasi lewat tes, serta risiko yang tersisa.

**Jangan menjalankan Phase 1+ sebelum hasil Phase 0 disampaikan**; selanjutnya pengembangan dapat dilanjutkan berdasarkan milestone di bawah.

---

## B. LATAR BELAKANG & PRODUK

### Problem
Proses mengubah video panjang menjadi beberapa Shorts membutuhkan analisis konten, pemotongan, reframing vertikal, subtitle, motion graphics, render, dan QA yang berulang. Pengguna ingin agent mengerjakan proses tersebut sampai klip siap dipakai, memakai komputer sendiri dan tanpa biaya API per-video untuk pipeline inti.

### Product vision
**OpenShorts Clipper** adalah sistem self-hosted, local-first yang menerima satu video sumber, mendeteksi momen menarik, menghasilkan 3–5 klip 9:16, menyusun subtitle/overlay dengan HyperFrames, menguji hasil, lalu menyerahkan MP4 beserta proyek editable dan laporan QC.

### Target utama
- Menjalankan clipping berbasis transkrip sepenuhnya lokal setelah instalasi model/dependensi.
- Menghasilkan klip relevan dengan visual rapi, audio sinkron, subtitle benar, dan output yang dapat direproduksi.
- Mengendalikan proses melalui CLI, REST API, MCP, serta skill agent yang bisa digunakan oleh Codex maupun Claude Code.
- Menyediakan pilihan analisis visual Google Gemini Web melalui Use Computer **hanya bila diperlukan dan pengguna telah mengizinkan upload**.
- Tidak menjadikan proyek ini sebagai modul Mabar pada tahap awal; arsitektur API harus tetap memungkinkan integrasi di kemudian hari.

### Non-goals — dilarang masuk MVP
- AI UGC video generation, AI actor, text-to-video, image-to-video, lip-sync generatif.
- ElevenLabs, voice cloning, dubbing, TTS.
- Monetisasi SaaS, billing, subscription, cloud account, third-party hosted rendering.
- Auto-publishing ke TikTok/Instagram/YouTube; tetap sebagai future extension.
- Menggantikan fungsi AI video generation Google Flow/Veo.
- Mengandalkan Gemini browser sebagai satu-satunya jalur analisis.

---

## C. DESAIN SISTEM (TARGET)

### Components
1. **OpenShorts Core — Python / FastAPI / FFmpeg:** ingestion, FFprobe, ASR (faster-whisper), scene boundaries, candidate selection, clip extraction, face-tracking/reframing, job API.
2. **Local Model Provider — Ollama/OpenAI-compatible endpoint:** memilih momen menarik melalui analisis transcript; konfigurasi `LLM_BASE_URL`, `LLM_MODEL`, timeout, token context, validation of structured JSON.
3. **HyperFrames Worker — Node.js 22+ / FFmpeg:** membuat dan merender komposisi HTML/CSS/GSAP dengan subtitle, title, hook, overlay, motion graphics dan audio sumber.
4. **Agent Orchestrator — Claude Code/Codex via skills:** membuat keputusan, mengontrol tools yang terdaftar, mengevaluasi quality gate, melakukan revisi terbatas, menyusun hasil.
5. **Optional Gemini Browser Analyzer:** interactive, opt-in, human-authenticated browser session, video visual analysis only. Tidak bergantung pada API Gemini dan tidak pernah melewati CAPTCHA/rate limits.
6. **Local Dashboard:** jobs, clip candidates, transcript, preview, presets, QA results dan settings.
7. **Local Artifact Store:** file dan manifest proyek, metadata, cache hasil analisis, output final; file lokal terlebih dahulu, S3 tidak diperlukan.

### Pipeline
`Local MP4 -> ffprobe -> transcription/scene detection -> LLM-ranked candidates -> timestamp verification -> OpenShorts crop/clip -> editable timeline manifest -> HyperFrames composition -> render MP4 -> automated QC -> final assets`.

Jika HyperFrames gagal tetapi clipper dasar sehat, sistem harus bisa mengeluarkan MP4 sederhana dari FFmpeg dengan status `NEEDS_REVIEW` atau fallback yang eksplisit. Jangan membakar subtitle dua kali: OpenShorts menyediakan word timestamps, HyperFrames yang menjadi renderer final subtitle ketika mode enhanced aktif.

### Module boundaries
- Python bertanggung jawab atas *media understanding* dan cut/crop.
- Node/HyperFrames bertanggung jawab atas *visual composition* dan rendering overlay final.
- AI agent memberi keputusan dan instruksi melalui API/CLI, tidak menyunting binary media secara langsung.
- Semua pertukaran data menggunakan skema JSON berversi dan path lokal yang divalidasi.
- Jangan membuat tight coupling yang mengharuskan Claude sebagai provider tunggal. Agent bisa diganti ke Codex.

---

## D. FUNCTIONAL REQUIREMENTS

| ID | Requirement | Acceptance behavior |
|---|---|---|
| FR-01 | Upload/import video MP4/MOV dan sumber lokal | Job baru mendapatkan UUID, checksum SHA-256, metadata FFprobe dan path aman. URL YouTube via yt-dlp adalah opsi dengan akses internet dan mematuhi hak konten. |
| FR-02 | Validate media | Deteksi no-audio, video corrupt, resolusi, FPS, durasi, ukuran; error terstruktur. |
| FR-03 | Word-level transcription | `transcript.json` dan opsi SRT/VTT, timestamp millisecond, bahasa Indonesia/Inggris. |
| FR-04 | Scene detection | Shot/scene boundaries dan keyframes bisa digunakan untuk potong/reframe. |
| FR-05 | Local moment selection | LLM lokal membuat kandidat klip dengan start/end, hook, reasons, scores, keywords. JSON harus divalidasi; skor adalah estimasi, bukan jaminan viral. |
| FR-06 | Candidate ranking & de-duplication | Default 3–5 klip, configurable 15–60 detik, hindari overlap substansial, jaga konteks pembicaraan. |
| FR-07 | Smart reframing | Output 9:16 dengan fallback mode center, face-track, split speaker, screencast bila tersedia; fungsi visual AI yang memerlukan Gemini harus bisa dinonaktifkan. |
| FR-08 | Word-aligned clip editing | Trim in/out, add/remove segment, koreksi teks dan framing lewat UI atau API. |
| FR-09 | HyperFrames enhanced render | Buat komposisi per clip menggunakan local assets, kinetic captions, hook text, motion overlays dan safe area. Tidak ada CDN wajib saat render. |
| FR-10 | Plain FFmpeg fallback | Dapat menghasilkan output minimal jika HyperFrames tidak tersedia. Fallback dilaporkan transparan. |
| FR-11 | Agent tools | CLI/REST/MCP untuk create job, process, status, list candidates, recut, apply template, render, inspect QA, get output paths, cancel. |
| FR-12 | Job orchestration | State machine persisten, queue, job logs, retry terbatas dan idempotency per stage. |
| FR-13 | Automated QA | Cek existence, codec, durasi, resolusi, sample frames, black frame, silence, subtitle safe area dan drift timing sesuai kemampuan test. |
| FR-14 | Review mode | `AUTO` atau `REVIEW_REQUIRED`; di mode review hasil tidak dianggap approved otomatis. |
| FR-15 | Optional browser vision | Agent boleh meminta Use Computer pada Gemini bila risiko konten visual kompleks; user consent upload, timeout, file provenance, fallback. |
| FR-16 | Reproducible outputs | Manifest input, timestamp, model/prompt version, preset version, run hash dan output disimpan per job. |

### Non-functional requirements
- Pipeline inti **tanpa Gemini API key, fal.ai, ElevenLabs, layanan TTS, atau subscription**.
- Default offline-capable setelah paket/model terunduh; jangan mengklaim `YouTube URL` atau Gemini web berjalan offline.
- Docker Compose pada Linux/Pop!_OS; HyperFrames menggunakan Node.js 22+ di worker terpisah.
- Pengujian CPU-only harus tersedia, GPU NVIDIA optional dengan graceful fallback.
- Batasi concurrency ke 1 untuk baseline CPU; sesuaikan setelah benchmark nyata, jangan mengarang throughput.
- File input dan output dibatasi di workspace yang diizinkan; jangan expose API publik tanpa autentikasi/TLS.
- Telemetry outbound opt-in atau disabled; semua third-party network access didokumentasi.
- Credential tidak dicetak di log, tidak masuk git, `.env` di-ignore, example config aman.
- Job bisa diulang/restart tanpa menghasilkan file ganda korup.

---

## E. CONTRACT DATA & JOB STATES

### Canonical timeline manifest (contoh rancangan, belum final)
```json
{
  "schema_version": "1.0.0",
  "job_id": "<uuid>",
  "source": {
    "path": "assets/source.mp4",
    "sha256": "<sha256>",
    "duration_ms": 1800000
  },
  "clips": [
    {
      "clip_id": "clip_001",
      "source_in_ms": 91000,
      "source_out_ms": 133000,
      "score": 0.82,
      "score_type": "model_estimate",
      "reason": "Strong opening statement with complete context",
      "layout": { "mode": "face_track", "aspect_ratio": "9:16" },
      "caption_style": "kinetic_clean",
      "words": [{ "start_ms": 91000, "end_ms": 91350, "text": "Contoh" }],
      "overlays": [{ "type": "hook", "text": "Contoh judul", "at_ms": 0 }]
    }
  ]
}
```

Timestamp `words` harus jelas apakah referensinya *source-relative* atau *clip-relative*. Kontrak v1 direkomendasikan `source-relative` untuk transkrip dan transformasi yang eksplisit ke clip-relative pada worker render. Definisikan ini tegas di JSON Schema, test negative timestamps, offset, dan overlap. Hindari absolute filesystem paths di manifest yang akan dipindahkan antar komputer; gunakan path relatif job root.

### Status job
`CREATED -> INGESTING -> TRANSCRIBING -> ANALYZING -> SELECTING -> CLIPPING -> COMPOSING -> RENDERING -> QA -> COMPLETED`.

Terminal/alternatif: `FAILED`, `CANCELED`, `NEEDS_REVIEW`. Simpan `stage`, `error_code`, `attempt`, `timestamps`, `artifacts`. Retry per-stage maksimal 3 untuk kesalahan yang bisa diperbaiki; jangan retry CAPTCHA, unauthorized, billing, atau invalid source secara otomatis.

### Minimal tool API (desain; selaraskan dengan existing API)
- `create_job(input_path, settings) -> job_id`
- `process_job(job_id) -> accepted`
- `get_job_status(job_id) -> stage/progress/errors`
- `list_clip_candidates(job_id) -> ranked clips`
- `update_clip(job_id, clip_id, decisions) -> updated manifest`
- `render_clip(job_id, clip_id, preset) -> output_id`
- `inspect_output(job_id, clip_id) -> QA report`
- `get_artifacts(job_id) -> output paths`
- `cancel_job(job_id) -> canceled`

Implementasikan sebagai wrapper aman di atas fungsi OpenShorts yang ada. Jangan memberikan tools shell unrestricted kepada browser atau remote caller.

---

## F. HYPERFRAMES INTEGRATION

Gunakan `heygen-com/hyperframes` sebagai dependency yang *dipin* ke versi/tag kompatibel, bukan disalin/di-fork ke inti OpenShorts kecuali ada alasan teknis yang jelas. HyperFrames menggunakan Apache 2.0 dan renderer CLI lokal; jangan mengunci project ke layanan premium atau API HeyGen.

1. Install skill resmi core untuk agent menggunakan prosedur yang didukung upstream, misalnya `npx hyperframes skills update` pada project yang relevan setelah audit keamanan/dependensi.
2. Render composition dari file lokal: footage clipped, transcript timestamps, style JSON, audio/video source.
3. Buat minimal tiga preset: `clean_podcast`, `bold_kinetic`, `educational_screen`.
4. Gunakan `npx hyperframes lint`, `npx hyperframes check`, dan render CLI sesuai versi yang dipasang. Jangan asumsikan semua command lint/check tersedia persis sama tanpa verifikasi versi.
5. Output harus mencakup `composition/index.html`, assets lokal, manifest, render log dan MP4.
6. Cache result dan re-render hanya stage yang berubah. Jangan melakukan transcription ulang hanya untuk mengubah font/overlay.

---

## G. AI AGENT SKILL — `autonomous-clipper`

Skill harus **provider-agnostic** sehingga bekerja dengan Claude Code dan Codex. Isi minimal:
- Trigger dan prasyarat.
- Input contract dan schema.
- SOP `inspect -> transcribe -> rank -> verify -> clip -> compose -> render -> QA -> deliver`.
- Decision rubric: preserve context, opening hook, speech clarity, crop quality, subtitle readability, user objective.
- Quality gates; tool-use policy; maximum retries; request human approval bila diperlukan.
- Safe fallback jika provider Gemini web offline, session expired, atau hak upload tidak ada.
- Rules jangan memalsukan durasi, skor, benchmark, citations, atau status job.
- Contoh command dan dataset validasi.

Hindari menjalankan shell commands destruktif. Operasi filesystem dan GitHub harus berada dalam worktree/project yang diotorisasi. Agent bukan media renderer; seluruh transformasi harus melalui engine deterministik.

---

## H. GEMINI VIA USE COMPUTER — OPTIONAL FUTURE PROVIDER

- **Default OFF**. Jangan implementasikan sebagai dependency untuk MVP.
- Gunakan hanya browser session yang sah dan kemampuan computer-use yang tersedia secara resmi pada lingkungan agent tersebut.
- Agent meminta konfirmasi spesifik sebelum mengunggah video pribadi/sensitif ke Gemini, termasuk jika video belum pernah dipublikasikan.
- Kebutuhan analisis: visual hook, on-screen context, scene type, active speaker, layout recommendation; kembali sebagai rekomendasi JSON yang diverifikasi secara lokal.
- Penggunaan browser dapat gagal karena UI berubah, upload limits, login, CAPTCHA, rate limiting, Terms; jangan bypass.
- Tidak menganggap langganan Gemini web sebagai izin penggunaan otomatis tanpa batas. Verifikasi ketentuan layanan dan batas aktual ketika tahap ini dimulai.
- Simpan ringkasan dan provenance: video hash, clip start-end, waktu analisis, model/provider jika diketahui, response text, parse status dan human approval. Jangan menyimpan cookie/token browser.

---

## I. REPOSITORY STRUCTURE — TRANSITIONAL, NOT BIG-BANG REWRITE

**Phase 0 harus mempertahankan layout asal OpenShorts.** Jangan memindahkan ratusan berkas dan memutus import sekaligus. Tambahkan struktur berikut secara inkremental:

```text
openshorts-clipper/
├── AGENTS.md                      # agent-independent policy
├── CLAUDE.md                      # pointer to AGENTS.md, Claude-specific hints
├── docs/
│   ├── PRD.md
│   ├── ARCHITECTURE.md
│   ├── UPSTREAM_AUDIT.md
│   ├── LICENSE_AUDIT.md
│   ├── ROADMAP.md
│   ├── ACCEPTANCE_TESTS.md
│   └── ADR/0001-fork-and-worker-boundaries.md
├── schemas/                       # phase 1+
├── integrations/hyperframes/      # phase 2+
├── agent/skills/autonomous-clipper/# phase 3+
├── tests/smoke/                   # minimum tests
├── .github/workflows/             # optional non-destructive CI
├── .env.example                   # sanitized
├── docker-compose.yml            # preserve working baseline
└── <original OpenShorts files>    # leave untouched until refactor verified
```

Pastikan `.gitignore` menghindari `output/`, raw footage, `.env`, model weights, browser profiles, temporary renders, serta caches. Dokumen keputusan harus menyatakan bahwa `cloud/` tidak menjadi dependency runtime baru.

---

## J. LICENSE, UPSTREAM & SECURITY AUDIT — MANDATORY

- **OpenShorts core:** root MIT license, preserve copyright/license/NOTICE.
- **Exception:** `cloud/` memakai OpenShorts Commercial License, bukan MIT. Core tetap dapat dijalankan tanpa modul tersebut bila `BILLING_ENABLED` tidak aktif menurut dokumentasi upstream. Audit import dan dependensinya sebelum mencoba eksklusi.
- **HyperFrames:** Apache 2.0. Simpan license/NOTICE yang berlaku untuk dependency atau redistribusi.
- **Provenance:** repository `mutonby/openshorts` tercatat sebagai fork dari `kamilstanuch/Autocrop-vertical`; lakukan audit riwayat/atribusi dan kondisi lisensi kode warisan, jangan otomatis menyimpulkan semua konten upstream berlisensi MIT hanya karena root sekarang menampilkan MIT.
- Audit dependensi (`yt-dlp`, whisper, YOLO, models, fonts, assets, npm packages) termasuk lisensi weights/model dan kebijakan penggunaan komersial.
- Jangan memasukkan video demo, gambar, font, API token, browser cookie atau kredensial ke git tanpa hak dan kebutuhan.
- Secret scanning, dependency scanning, basic input validation, safe file paths, no arbitrary remote shell, network egress documented.
- Hindari membuka port Docker ke `0.0.0.0` untuk layanan sensitif tanpa kontrol akses; local dev default localhost ketika aman.
- Tidak menyentuh repo Mabar, folder `.agents` global atau file pribadi di luar project tanpa izin eksplisit.

---

## K. MILESTONES & DEFINITION OF DONE

### Phase 0 — GitHub Repository + Forensic Audit + Baseline **(KERJAKAN SEKARANG)**
Deliverables:
- Repo fork `openshorts-clipper` dibuat di akun pengguna (jika akses tersedia), `origin`/`upstream` tepat, baseline SHA tercatat.
- Working branch dan PR, `docs/PRD.md`, `docs/ARCHITECTURE.md`, `docs/UPSTREAM_AUDIT.md`, `docs/LICENSE_AUDIT.md`, `docs/ROADMAP.md`, `docs/ACCEPTANCE_TESTS.md`, `AGENTS.md`, `CLAUDE.md`.
- Inventaris entrypoint, Python dependencies, frontend, Docker, render service, APIs, feature flags, SaaS-only code, third-party calls, GPU requirements.
- Jalankan tes smoke upstream jika environment mendukung; bila tidak, tulis hasil `NOT_RUN` dan kebutuhan reproduksi. Jangan menyatakan PASS tanpa log/bukti.
- Buat rencana pemotongan fitur non-clipper dengan dependency map: `KEEP`, `DISABLE`, `REMOVE_LATER`, `AUDIT`.
- Laporan repository URL, branch/PR, commit SHA, audit findings, blocker, dan next milestone.

**Acceptance Phase 0:** repo sebenarnya ada atau blocker otorisasi dilaporkan; PR/revision sebenarnya ada; dokumen tersedia dan selaras; tidak ada perubahan yang memutus baseline tanpa alasan; audit lisensi menyebut pengecualian `cloud/` dan provenance historis.

### Phase 1 — Clipper-Only + Local Models
- Nonaktifkan UGC, TTS, dubbing, publishing, billing, dan cloud gallery di UI dan job workflow.
- Buat baseline headless untuk transcribe -> rank -> clip -> 9:16 export dengan local LLM.
- Integrasi Ollama, model configurable, validation, caching dan fallback.
- Lulus smoke test satu video lokal (atau fixture legal yang sudah tersedia) tanpa Gemini API/fal.ai/ElevenLabs.

### Phase 2 — HyperFrames Enhanced Rendering
- Implementasi schema versioned timeline dan Python -> Node worker boundary.
- Presets, subtitle word-alignment, motion overlay, render logs, output editable.
- Jangan double burn subtitle. Lulus QA untuk 3 preset pada fixture.

### Phase 3 — Autonomous Agent + MCP/CLI
- Skill `autonomous-clipper` untuk Codex & Claude Code.
- Multi-stage workflow, retry/idempotency, decision log, QA pass/fail, review gate.
- Agent memproses satu video menjadi 3–5 hasil dan menulis final manifest.

### Phase 4 — Optional Gemini Browser Vision
- Browser provider with explicit consent, limited availability, error handling, fallback.
- Tanpa mempengaruhi successful local-only pipeline.

### Future (Out of Scope)
- Mass batch processing, schedules, Mabar integration, social publishing, multi-user SaaS.

---

## L. ACCEPTANCE TEST SCENARIOS

1. **Single speaker** — input horizontal dengan monolog, 3 kandidat relevan, crop wajah stabil, subtitle sinkron.
2. **Two speakers** — percakapan; pemilihan layout tidak menghilangkan pembicara, fallback split/manual tersedia.
3. **Screencast/tutorial** — konten layar tidak terpotong secara fatal; mode reframe alternatif tersedia.
4. **Silent video** — sistem melaporkan batasan local transcript pipeline; tidak mengarang transkrip.
5. **No network mode** — local file + downloaded models + Ollama menghasilkan output atau error lokal deterministik; tidak menghubungi API eksternal.
6. **No keys** — proses clipping utama tetap berjalan tanpa `GEMINI_API_KEY`, `FAL_KEY`, `ELEVENLABS_API_KEY`.
7. **Render failure** — status/error/retry benar, fallback aman, tidak meninggalkan `COMPLETED` palsu.
8. **Restart/resume** — work item dapat dilanjutkan tanpa kehilangan source manifest.
9. **Security** — path traversal ditolak; file rahasia tidak terekspos; Git history bebas key.
10. **Verification** — MP4 dengan H.264/AAC atau codec yang telah ditetapkan, rasio 9:16, metadata duration/fps valid; subtitle tidak overcrop. Definisikan toleransi sinkronisasi empiris dari fixture.

Jangan klaim throughput atau kualitas komersial tanpa benchmark nyata; catat hardware CPU/GPU, ukuran/durasi input, model, waktu eksekusi tiap stage dan hasilnya.

---

## M. FIRST-RUN REPORT FORMAT FOR CLAUDE WORK

Di akhir Phase 0 tampilkan:

1. **GitHub:** owner/repo URL, visibilitas repo, status fork, `origin`, `upstream`, baseline commit SHA, branch, PR URL jika ada.
2. **What was changed:** daftar file diciptakan atau diubah, ringkasan commit.
3. **Architecture audit:** tabel KEEP/DISABLE/REMOVE_LATER/AUDIT berikut alasan dan dependensi.
4. **License/security audit:** apa yang diketahui, apa yang belum dipastikan, risiko distribusi.
5. **Validation evidence:** command dan ringkasan output PASS/FAIL/NOT_RUN; bedakan test cloud dari local user's PC.
6. **Blocked actions:** izin/koneksi yang diperlukan (jika ada) dan apa dampaknya.
7. **Next actions:** pekerjaan Phase 1 terurut dan estimasi complexity tanpa menjanjikan hasil asynchronous.

**Definition of done pertama: ada repository yang benar-benar dibuat, baseline bisa dilacak, audit terverifikasi, instruksi developer/agent jelas, dan tidak ada penghapusan massal.**

---

## N. REFERENCE SOURCES

- OpenShorts: https://github.com/mutonby/openshorts
- OpenShorts MIT root: https://github.com/mutonby/openshorts/blob/main/LICENSE
- OpenShorts NOTICE: https://github.com/mutonby/openshorts/blob/main/NOTICE
- OpenShorts commercial exception: https://github.com/mutonby/openshorts/blob/main/cloud/LICENSE
- HyperFrames: https://github.com/heygen-com/hyperframes
- HyperFrames agent conventions: https://github.com/heygen-com/hyperframes/blob/main/AGENTS.md
- Gemini Apps video files help: https://support.google.com/gemini/answer/14903178

