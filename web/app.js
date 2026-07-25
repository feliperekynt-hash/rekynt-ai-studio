document.addEventListener("DOMContentLoaded", () => {
  let activeJobId = null;
  let pollInterval = null;

  // Gerenciador de Sessão Limpa em Memória (sessionStorage)
  let sessionVideos = JSON.parse(sessionStorage.getItem("rekynt_session_videos") || "[]");
  let sessionOutputs = JSON.parse(sessionStorage.getItem("rekynt_session_outputs") || "[]");

  // Login Elements
  const modalLogin = document.getElementById("modal-login");
  const formLogin = document.getElementById("form-login");
  const loginEmail = document.getElementById("login-email");
  const userEmailDisplay = document.getElementById("user-email-display");
  const btnLogout = document.getElementById("btn-logout");
  const btnResetSession = document.getElementById("btn-reset-session");

  // Phone Player Elements
  const phoneVideoPlayer = document.getElementById("phone-video-player");
  const simulatedBg = document.getElementById("simulated-video-bg");
  const phoneLoaderOverlay = document.getElementById("phone-loader-overlay");
  const phoneLoaderTitle = document.getElementById("phone-loader-title");
  const phoneLoaderPct = document.getElementById("phone-loader-pct");
  const phoneStatusSubtitle = document.getElementById("phone-status-subtitle");
  const btnPhoneDownload = document.getElementById("btn-phone-download");

  function checkSession() {
    const storedEmail = localStorage.getItem("rekynt_studio_email") || "corretor.rekynt@gmail.com";
    userEmailDisplay.textContent = storedEmail;
    if (!localStorage.getItem("rekynt_studio_email")) {
      modalLogin.style.display = "flex";
    } else {
      modalLogin.style.display = "none";
    }
  }

  formLogin.addEventListener("submit", (e) => {
    e.preventDefault();
    const email = loginEmail.value.trim();
    if (email) {
      localStorage.setItem("rekynt_studio_email", email);
      userEmailDisplay.textContent = email;
      modalLogin.style.display = "none";
    }
  });

  btnLogout.addEventListener("click", () => {
    localStorage.removeItem("rekynt_studio_email");
    resetCurrentSession();
    checkSession();
  });

  btnResetSession.addEventListener("click", () => {
    resetCurrentSession();
    alert("Sessão zerada com sucesso! Você pode iniciar uma nova edição limpa.");
  });

  function resetCurrentSession() {
    sessionVideos = [];
    sessionOutputs = [];
    sessionStorage.removeItem("rekynt_session_videos");
    sessionStorage.removeItem("rekynt_session_outputs");
    
    document.getElementById("input-drive-url").value = "";
    document.getElementById("upload-progress").style.display = "none";
    document.getElementById("job-status-card").style.display = "none";
    phoneLoaderOverlay.style.display = "none";
    btnPhoneDownload.style.display = "none";

    phoneVideoPlayer.style.display = "none";
    phoneVideoPlayer.pause();
    phoneVideoPlayer.src = "";
    simulatedBg.style.display = "block";
    phoneStatusSubtitle.textContent = "Envie um vídeo para visualizar";

    renderSessionMedia();
  }

  // Upload & Drive Elements
  const fileInput = document.getElementById("file-input");
  const uploadDropzone = document.getElementById("upload-dropzone");
  const uploadProgress = document.getElementById("upload-progress");
  const uploadProgressLabel = document.getElementById("upload-progress-label");
  const uploadProgressBar = document.getElementById("upload-progress-bar");
  const inputDriveUrl = document.getElementById("input-drive-url");
  const btnImportDrive = document.getElementById("btn-import-drive");

  const selectVideo = document.getElementById("select-video");
  const btnStartRender = document.getElementById("btn-start-render");

  const jobStatusCard = document.getElementById("job-status-card");
  const jobStatusTitle = document.getElementById("job-status-title");
  const jobStatusMsg = document.getElementById("job-status-msg");
  const jobSpinner = document.getElementById("job-spinner");
  const outputsList = document.getElementById("outputs-list");

  // Drag & Drop
  ["dragenter", "dragover"].forEach(eventName => {
    uploadDropzone.addEventListener(eventName, (e) => {
      e.preventDefault();
      uploadDropzone.style.background = "rgba(255, 107, 53, 0.12)";
    });
  });

  ["dragleave", "drop"].forEach(eventName => {
    uploadDropzone.addEventListener(eventName, (e) => {
      e.preventDefault();
      uploadDropzone.style.background = "rgba(255, 107, 53, 0.04)";
    });
  });

  uploadDropzone.addEventListener("drop", (e) => {
    const files = e.dataTransfer.files;
    if (files.length > 0) uploadFileDirectly(files[0]);
  });

  fileInput.addEventListener("change", () => {
    if (fileInput.files.length > 0) uploadFileDirectly(fileInput.files[0]);
  });

  async function uploadFileDirectly(file) {
    uploadProgress.style.display = "block";
    uploadProgressLabel.textContent = `Enviando '${file.name}'...`;
    uploadProgressBar.style.width = "50%";

    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await fetch("/api/upload", { method: "POST", body: formData });
      const data = await res.json();

      if (data.success) {
        uploadProgressBar.style.width = "100%";
        uploadProgressLabel.textContent = `✅ Vídeo '${data.filename}' pronto para edição!`;
        
        addVideoToSession(data.filename, data.rel_path);
      } else {
        uploadProgressLabel.textContent = `❌ Erro: ${data.error || "Falha no envio"}`;
      }
    } catch (err) {
      uploadProgressLabel.textContent = "❌ Erro de conexão ao enviar vídeo.";
    }
  }

  // Importar Google Drive
  btnImportDrive.addEventListener("click", async () => {
    const url = inputDriveUrl.value.trim();
    if (!url) {
      alert("Por favor, cole o link da pasta do Google Drive.");
      return;
    }

    btnImportDrive.disabled = true;
    btnImportDrive.textContent = "Importando...";

    try {
      const res = await fetch("/api/upload-drive-url", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ drive_url: url })
      });

      const data = await res.json();
      if (data.success) {
        alert(data.message);
        inputDriveUrl.value = "";
        
        if (data.videos && data.videos.length > 0) {
          data.videos.forEach(v => {
            if (!sessionVideos.some(sv => sv.rel_path === v.rel_path)) {
              sessionVideos.unshift(v);
            }
          });
          sessionStorage.setItem("rekynt_session_videos", JSON.stringify(sessionVideos));
          renderSessionMedia(data.rel_path);
        } else if (data.filename && data.rel_path) {
          addVideoToSession(data.filename, data.rel_path);
        }
      } else {
        alert("Erro: " + (data.error || "Falha na importação"));
      }
    } catch (err) {
      alert("Erro ao conectar ao Google Drive.");
    } finally {
      btnImportDrive.disabled = false;
      btnImportDrive.textContent = "Importar";
    }
  });

  function addVideoToSession(filename, rel_path) {
    if (!sessionVideos.some(v => v.rel_path === rel_path)) {
      sessionVideos.unshift({ filename, rel_path });
      sessionStorage.setItem("rekynt_session_videos", JSON.stringify(sessionVideos));
    }
    renderSessionMedia(rel_path);
  }

  function addOutputToSession(output_file) {
    if (!sessionOutputs.includes(output_file)) {
      sessionOutputs.unshift(output_file);
      sessionStorage.setItem("rekynt_session_outputs", JSON.stringify(sessionOutputs));
    }
    renderOutputsList();
  }

  function renderSessionMedia(selected_rel_path = null) {
    selectVideo.innerHTML = "";

    if (sessionVideos.length === 0) {
      const opt = document.createElement("option");
      opt.value = "";
      opt.textContent = "Nenhum vídeo nesta sessão - Envie do celular ou Drive acima";
      selectVideo.appendChild(opt);
    } else {
      sessionVideos.forEach(v => {
        const opt = document.createElement("option");
        opt.value = v.rel_path;
        opt.textContent = v.filename;
        selectVideo.appendChild(opt);
      });
      if (selected_rel_path) {
        selectVideo.value = selected_rel_path;
      }
    }

    updatePhonePreview();
    renderOutputsList();
  }

  function updatePhonePreview() {
    if (selectVideo.value && !activeJobId) {
      simulatedBg.style.display = "none";
      phoneVideoPlayer.style.display = "block";
      phoneVideoPlayer.src = "/assets/" + selectVideo.value;
      phoneVideoPlayer.play();
      phoneStatusSubtitle.textContent = `▶ Tocando vídeo da casa: ${selectVideo.options[selectVideo.selectedIndex]?.text || ''}`;
    }
  }

  selectVideo.addEventListener("change", updatePhonePreview);

  function renderOutputsList() {
    if (sessionOutputs.length === 0) {
      outputsList.innerHTML = `<div class="empty-state">Nenhum Reels gerado nesta sessão ainda. Envie um vídeo ao lado.</div>`;
      return;
    }

    outputsList.innerHTML = "";
    sessionOutputs.forEach(output => {
      const item = document.createElement("div");
      item.className = "output-item";
      item.innerHTML = `
        <div class="output-info">
          <span class="output-name">${output}</span>
          <span class="output-tag">Rekynt 9:16 Full HD • Edição Automática IA</span>
        </div>
        <div class="output-actions">
          <button onclick="playInPhone('${output}')" class="btn btn-outline" style="padding:6px 10px; font-size:11px;">▶ Assistir no Celular</button>
          <a href="/assets/output/${output}" target="_blank" download class="btn btn-primary" style="padding:6px 12px; font-size:11px;">📥 Baixar</a>
        </div>
      `;
      outputsList.appendChild(item);
    });
  }

  window.playInPhone = function(output_file) {
    phoneLoaderOverlay.style.display = "none";
    simulatedBg.style.display = "none";
    phoneVideoPlayer.style.display = "block";
    phoneVideoPlayer.src = "/assets/output/" + output_file;
    phoneVideoPlayer.play();
    phoneStatusSubtitle.textContent = "▶ Reels Finalizado Tocando no Celular!";

    btnPhoneDownload.style.display = "flex";
    btnPhoneDownload.href = "/assets/output/" + output_file;
  };

  // 1-Clique Render
  btnStartRender.addEventListener("click", async () => {
    if (!selectVideo.value) {
      alert("Por favor, envie ou importe um vídeo primeiro antes de gerar o Reels.");
      return;
    }

    jobStatusCard.style.display = "block";
    if (jobSpinner) jobSpinner.style.display = "inline-block";

    // EXIBIR ANIMAÇÃO DE RENDER DENTRO DO PRÓPRIO CELULAR!
    simulatedBg.style.display = "block";
    phoneVideoPlayer.style.display = "none";
    phoneVideoPlayer.pause();
    phoneLoaderOverlay.style.display = "flex";
    phoneLoaderTitle.textContent = "IA Editando Reels do Imóvel...";
    phoneLoaderPct.textContent = "0%";
    phoneStatusSubtitle.textContent = "⏳ IA Editando Vídeo do Imóvel...";

    jobStatusTitle.textContent = "Criando Reels do Imóvel com IA...";
    jobStatusMsg.textContent = "Processando vídeo da sessão atual em alta fidelidade...";
    btnStartRender.disabled = true;

    const currentEmail = localStorage.getItem("rekynt_studio_email") || "corretor.rekynt@gmail.com";

    try {
      const res = await fetch("/api/process", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          video: selectVideo.value,
          user_email: currentEmail
        })
      });

      const data = await res.json();
      if (data.success) {
        activeJobId = data.job_id;
        startPollingJobStatus();
      } else {
        jobStatusMsg.textContent = "Erro: " + (data.error || "Falha na solicitação");
        btnStartRender.disabled = false;
        phoneLoaderOverlay.style.display = "none";
      }
    } catch (err) {
      jobStatusMsg.textContent = "Erro de conexão com o servidor de renderização.";
      btnStartRender.disabled = false;
      phoneLoaderOverlay.style.display = "none";
    }
  });

  function startPollingJobStatus() {
    if (pollInterval) clearInterval(pollInterval);
    let pollStep = 0;

    pollInterval = setInterval(async () => {
      if (!activeJobId) return;
      pollStep++;

      try {
        const res = await fetch(`/api/status/${activeJobId}`);
        if (res.ok) {
          const job = await res.json();
          
          const fillBar = document.getElementById("job-progress-bar");
          if (fillBar && job.status === "processing") {
            const pct = Math.min(95, pollStep * 12);
            fillBar.style.width = pct + "%";
            jobStatusMsg.textContent = `Edição IA: ${pct}% concluído...`;
            phoneLoaderPct.textContent = `${pct}%`;
          }

          if (job.status === "completed") {
            clearInterval(pollInterval);
            pollInterval = null;
            activeJobId = null;

            if (jobSpinner) jobSpinner.style.display = "none";

            jobStatusTitle.textContent = "✅ Reels do Imóvel Concluído!";
            jobStatusMsg.textContent = "Seu vídeo está 100% pronto! Assista e baixe no celular ao centro.";
            if (fillBar) fillBar.style.width = "100%";
            btnStartRender.disabled = false;

            if (job.output_file) {
              addOutputToSession(job.output_file);
              playInPhone(job.output_file);
            }
          } else if (job.status === "failed") {
            clearInterval(pollInterval);
            pollInterval = null;
            activeJobId = null;

            if (jobSpinner) jobSpinner.style.display = "none";
            phoneLoaderOverlay.style.display = "none";
            jobStatusTitle.textContent = "❌ Falha na Edição";
            jobStatusMsg.textContent = job.error || "Erro na renderização";
            btnStartRender.disabled = false;
          }
        }
      } catch (err) {
        console.error(err);
      }
    }, 1000);
  }

  checkSession();
  renderSessionMedia();
});
