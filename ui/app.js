// Audio Extractor CD by AO Labs - Frontend Controller (Flask API version)

document.addEventListener('DOMContentLoaded', () => {
  console.log('[app.js] DOMContentLoaded fired');

  // DOM Elements
  const driveSelect = document.getElementById('drive-select');
  const btnRefreshDrives = document.getElementById('btn-refresh-drives');
  const statusText = document.getElementById('status-text');
  
  const coverImg = document.getElementById('cover-img');
  const btnSearchCoverOnline = document.getElementById('btn-search-cover-online');
  const btnLoadCoverLocal = document.getElementById('btn-load-cover-local');
  const metaSourceTag = document.getElementById('meta-source-tag');

  const inputAlbum = document.getElementById('input-album');
  const inputArtist = document.getElementById('input-artist');
  const inputYear = document.getElementById('input-year');
  const inputGenre = document.getElementById('input-genre');

  const formatPills = document.querySelectorAll('#format-pills .pill');
  const qualitySelect = document.getElementById('quality-select');
  const outputPathInput = document.getElementById('output-path-input');
  const btnBrowseFolder = document.getElementById('btn-browse-folder');
  const btnApplyArtistAll = document.getElementById('btn-apply-artist-all');

  btnApplyArtistAll.addEventListener('click', () => {
    const mainArtist = inputArtist.value.trim();
    if (!mainArtist) return;
    
    currentTracks.forEach(tr => tr.artist = mainArtist);
    renderTracksTable();
  });

  const tracksTbody = document.getElementById('tracks-tbody');
  const trackCountLabel = document.getElementById('track-count-label');
  const checkHeaderAll = document.getElementById('check-header-all');
  const btnSelectAll = document.getElementById('btn-select-all');
  const btnDeselectAll = document.getElementById('btn-deselect-all');

  const btnStartRip = document.getElementById('btn-start-rip');
  const btnKofi = document.getElementById('btn-kofi');

  // Modals
  const progressModal = document.getElementById('progress-modal');
  const progressTitle = document.getElementById('progress-title');
  const progressBarFill = document.getElementById('progress-bar-fill');
  const progressStatusText = document.getElementById('progress-status-text');
  const progressPercentageText = document.getElementById('progress-percentage-text');
  const btnCancelRip = document.getElementById('btn-cancel-rip');

  const coverSearchModal = document.getElementById('cover-search-modal');
  const btnCloseCoverModal = document.getElementById('btn-close-cover-modal');
  const coverSearchInput = document.getElementById('cover-search-input');
  const btnExecuteCoverSearch = document.getElementById('btn-execute-cover-search');
  const coverResultsGrid = document.getElementById('cover-results-grid');

  const albumSearchModal = document.getElementById('album-search-modal');
  const btnOpenAlbumSearch = document.getElementById('btn-open-album-search');
  const btnCloseAlbumModal = document.getElementById('btn-close-album-modal');
  const albumSearchInput = document.getElementById('album-search-input');
  const btnExecuteAlbumSearch = document.getElementById('btn-execute-album-search');
  const albumResultsList = document.getElementById('album-results-list');

  const checkAutoOpen = document.getElementById('check-auto-open');
  const btnAcceptRip = document.getElementById('btn-accept-rip');

  // State
  let currentFormat = 'flac';
  let currentTracks = [];
  let playingTrackNumber = null;

  updateQualityOptions(currentFormat);

  // Initialize with the user's default Music folder
  apiGet('/api/get_default_music_dir').then(res => {
    if (res && res.path) {
      outputPathInput.value = res.path;
    } else {
      outputPathInput.value = "C:/Users/Public/Music";
    }
  });

  statusText.textContent = "Haz clic en 🔄 para buscar lectoras de CD.";

  // ── Helper: API call via fetch ────────────────────────
  async function apiGet(endpoint) {
    const res = await fetch(endpoint);
    return res.json();
  }

  async function apiPost(endpoint, body = {}) {
    const res = await fetch(endpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    });
    return res.json();
  }

  // ── Format Pills ──────────────────────────────────────
  formatPills.forEach(pill => {
    pill.addEventListener('click', () => {
      formatPills.forEach(p => p.classList.remove('active'));
      pill.classList.add('active');
      currentFormat = pill.dataset.format;
      updateQualityOptions(currentFormat);
      btnStartRip.querySelector('span').textContent = `INICIAR EXTRACCIÓN A ${currentFormat.toUpperCase()}`;
    });
  });

  function updateQualityOptions(fmt) {
    qualitySelect.innerHTML = '';
    if (fmt === 'flac') {
      qualitySelect.innerHTML = `
        <option value="max">Compresión FLAC Máxima (Nivel 8)</option>
        <option value="normal">Compresión Estándar (Nivel 5)</option>
      `;
    } else if (fmt === 'mp3') {
      qualitySelect.innerHTML = `
        <option value="320">MP3 320 kbps CBR (Máxima Calidad)</option>
        <option value="256">256 kbps CBR</option>
        <option value="v0">VBR V0 (~240 kbps Alta Calidad)</option>
      `;
    } else if (fmt === 'wav') {
      qualitySelect.innerHTML = `
        <option value="pcm">Audio PCM Sin Comprimir 16-bit 44.1kHz</option>
      `;
    } else if (fmt === 'aac' || fmt === 'm4a') {
      qualitySelect.innerHTML = `
        <option value="256">AAC 256 kbps (Calidad iTunes)</option>
        <option value="320">AAC 320 kbps</option>
      `;
    } else if (fmt === 'ogg') {
      qualitySelect.innerHTML = `
        <option value="q6">Vorbis Q6 (~192 kbps)</option>
        <option value="q8">Vorbis Q8 (~256 kbps)</option>
      `;
    } else if (fmt === 'opus') {
      qualitySelect.innerHTML = `
        <option value="160">Opus 160 kbps (Alta Eficiencia)</option>
      `;
    }
  }

  // ── Drive Loading ─────────────────────────────────────
  async function loadDrives() {
    statusText.textContent = "Buscando lectoras de CD...";
    try {
      const drives = await apiGet('/api/drives');
      driveSelect.innerHTML = '';
      if (!drives || drives.length === 0) {
        driveSelect.innerHTML = '<option value="">No se encontraron lectoras de CD</option>';
        statusText.textContent = "Sin lectoras de CD detectadas.";
        return;
      }

      let selectedDrive = null;
      drives.forEach(d => {
        const opt = document.createElement('option');
        opt.value = d.drive;
        opt.textContent = d.label;
        if (d.has_disc && !selectedDrive) {
          selectedDrive = d.drive;
        }
        driveSelect.appendChild(opt);
      });

      if (!selectedDrive && drives.length > 0) {
        selectedDrive = drives[0].drive;
      }

      if (selectedDrive) {
        driveSelect.value = selectedDrive;
        onDriveSelected(selectedDrive);
      } else {
        statusText.textContent = "Selecciona un lector de CD.";
      }
    } catch (err) {
      console.error("Error loading drives:", err);
      statusText.textContent = "Error al listar unidades.";
    }
  }

  // Auto-load drives on page load (safe with Flask — no deadlocks)
  loadDrives();

  btnRefreshDrives.addEventListener('click', loadDrives);

  const btnEjectCd = document.getElementById('btn-eject-cd');
  if (btnEjectCd) {
    btnEjectCd.addEventListener('click', async () => {
      const drive = driveSelect.value;
      if (!drive) {
        alert("Selecciona una unidad de CD primero.");
        return;
      }
      await apiPost('/api/eject_cd', { drive: drive });
      statusText.textContent = "Bandeja expulsada.";
      metaSourceTag.textContent = "No se detectaron los metadatos automáticamente";
      inputAlbum.value = "";
      inputArtist.value = "";
      inputYear.value = "";
      inputGenre.value = "";
      coverImg.src = "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='300' height='300' viewBox='0 0 24 24' fill='none' stroke='%233a4161' stroke-width='1.5'><rect x='3' y='3' width='18' height='18' rx='2'/><circle cx='12' cy='12' r='4'/><path d='M12 2v4M12 18v4M2 12h4M18 12h4'/></svg>";
      
      currentTracks = [];
      renderTracksTable();
      setTimeout(loadDrives, 1500); // refresh after tray opens
    });
  }

  driveSelect.addEventListener('change', (e) => {
    const val = e.target.value;
    if (val) {
      onDriveSelected(val);
    }
  });

  // ── CD Info Loading ───────────────────────────────────
  async function onDriveSelected(driveLetter) {
    statusText.textContent = `Leyendo pistas del CD en ${driveLetter}...`;
    metaSourceTag.textContent = "Leyendo...";
    
    try {
      const res = await apiPost('/api/cd_info', { drive: driveLetter });
      
      if (!res || !res.success) {
        statusText.textContent = (res && res.message) ? res.message : "No se pudo leer el disco.";
        tracksTbody.innerHTML = `<tr><td colspan="6" class="empty-msg">${(res && res.message) ? res.message : "Error al leer disco"}</td></tr>`;
        return;
      }

      statusText.textContent = `Disco detectado (${res.tracks.length} pistas en ${driveLetter}).`;
      metaSourceTag.textContent = res.found_online ? `MusicBrainz: ${res.disc_id.substring(0, 8)}...` : "No se detectaron los metadatos automáticamente";
      
      inputAlbum.value = res.found_online ? (res.album || '') : '';
      inputArtist.value = res.found_online ? (res.artist || '') : '';
      inputYear.value = res.found_online ? (res.year || '') : '';
      inputGenre.value = res.found_online ? (res.genre || '') : '';

      if (res.cover_preview) {
        coverImg.src = res.cover_preview;
      } else {
        coverImg.src = "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='300' height='300' viewBox='0 0 24 24' fill='none' stroke='%233a4161' stroke-width='1.5'><rect x='3' y='3' width='18' height='18' rx='2'/><circle cx='12' cy='12' r='4'/></svg>";
      }

      currentTracks = res.tracks;
      renderTracksTable();
    } catch (err) {
      console.error("Error requesting CD info:", err);
      statusText.textContent = "Error de lectura de metadatos.";
    }
  }

  // ── Tracks Table ──────────────────────────────────────
  function renderTracksTable() {
    tracksTbody.innerHTML = '';
    trackCountLabel.textContent = `${currentTracks.length} Pistas`;

    currentTracks.forEach((tr, idx) => {
      const isPlaying = (playingTrackNumber === tr.number);
      const trEl = document.createElement('tr');
      trEl.innerHTML = `
        <td><input type="checkbox" class="track-check" data-index="${idx}" ${tr.selected ? 'checked' : ''}></td>
        <td><strong>${tr.number}</strong></td>
        <td>
          <button class="btn-play-track ${isPlaying ? 'playing' : ''}" data-number="${tr.number}">
            ${isPlaying ? '⏹ Detener' : '▶ Escuchar'}
          </button>
        </td>
        <td><input type="text" class="track-input-edit" data-index="${idx}" value="${escapeHtml(tr.title)}" onfocus="this.select()"></td>
        <td><input type="text" class="track-artist-edit" data-index="${idx}" value="${escapeHtml(tr.artist || 'Artista Desconocido')}" onfocus="this.select()"></td>
        <td><code>${tr.duration}</code></td>
      `;
      tracksTbody.appendChild(trEl);
    });

    document.querySelectorAll('.track-check').forEach(chk => {
      chk.addEventListener('change', (e) => {
        const i = parseInt(e.target.dataset.index);
        currentTracks[i].selected = e.target.checked;
      });
    });

    document.querySelectorAll('.track-input-edit').forEach(inp => {
      inp.addEventListener('input', (e) => {
        const i = parseInt(e.target.dataset.index);
        currentTracks[i].title = e.target.value;
      });
    });

    document.querySelectorAll('.track-artist-edit').forEach(inp => {
      inp.addEventListener('input', (e) => {
        const i = parseInt(e.target.dataset.index);
        currentTracks[i].artist = e.target.value;
      });
    });

    document.querySelectorAll('.btn-play-track').forEach(btn => {
      btn.addEventListener('click', async () => {
        // Use btn (the actual button element) not e.target (could be text node inside)
        const trNum = parseInt(btn.dataset.number);
        const driveLetter = driveSelect.value;
        if (!driveLetter || isNaN(trNum)) return;

        if (playingTrackNumber === trNum) {
          // Stop current track
          await apiPost('/api/stop_audio');
          playingTrackNumber = null;
        } else {
          // Stop any previous track first, then play new one
          if (playingTrackNumber !== null) {
            await apiPost('/api/stop_audio');
          }
          const res = await apiPost('/api/play_track', { drive: driveLetter, track: trNum });
          if (res && res.success) {
            playingTrackNumber = trNum;
          } else {
            alert("No se pudo reproducir la pista de audio.");
          }
        }
        renderTracksTable();
      });
    });
  }

  function escapeHtml(str) {
    return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }

  // ── Selection Controls ────────────────────────────────
  checkHeaderAll.addEventListener('change', (e) => {
    const isChecked = e.target.checked;
    currentTracks.forEach(t => t.selected = isChecked);
    document.querySelectorAll('.track-check').forEach(chk => chk.checked = isChecked);
  });

  btnSelectAll.addEventListener('click', () => {
    checkHeaderAll.checked = true;
    currentTracks.forEach(t => t.selected = true);
    document.querySelectorAll('.track-check').forEach(chk => chk.checked = true);
  });

  btnDeselectAll.addEventListener('click', () => {
    checkHeaderAll.checked = false;
    currentTracks.forEach(t => t.selected = false);
    document.querySelectorAll('.track-check').forEach(chk => chk.checked = false);
  });

  // ── Folder Browse (manual input since no native dialog in browser) ──
  btnBrowseFolder.addEventListener('click', async () => {
    try {
      const res = await apiGet('/api/browse_folder');
      if (res && res.success && res.path) {
        outputPathInput.value = res.path;
      }
    } catch (err) {
      console.error("Error browsing folder:", err);
    }
  });

  // Note: Local cover file selection uses a file input instead of native dialog
  btnLoadCoverLocal.addEventListener('click', () => {
    const fileInput = document.createElement('input');
    fileInput.type = 'file';
    fileInput.accept = 'image/*';
    fileInput.addEventListener('change', (e) => {
      const file = e.target.files[0];
      if (file) {
        const reader = new FileReader();
        reader.onload = async (ev) => {
          const dataUrl = ev.target.result;
          coverImg.src = dataUrl;
          metaSourceTag.textContent = "Portada Local";
          
          // Send to backend so it gets embedded in the FLAC/MP3 files
          await apiPost('/api/set_cover_url', { url: dataUrl });
        };
        reader.readAsDataURL(file);
      }
    });
    fileInput.click();
  });

  // ── Online Cover Search ───────────────────────────────
  btnSearchCoverOnline.addEventListener('click', () => {
    coverSearchModal.classList.remove('hidden');
    let qArtist = inputArtist.value.trim() === 'Artista Desconocido' ? '' : inputArtist.value.trim();
    let qAlbum = inputAlbum.value.trim().startsWith('Álbum CD (') ? '' : inputAlbum.value.trim();
    const query = `${qArtist} ${qAlbum}`.trim();
    coverSearchInput.value = query;
    if (query) {
      executeCoverSearch(query);
    }
  });

  btnCloseCoverModal.addEventListener('click', () => {
    coverSearchModal.classList.add('hidden');
  });

  btnExecuteCoverSearch.addEventListener('click', () => {
    executeCoverSearch(coverSearchInput.value);
  });

  coverSearchInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      executeCoverSearch(coverSearchInput.value);
    }
  });

  async function executeCoverSearch(query) {
    if (!query.trim()) return;
    coverResultsGrid.innerHTML = '<div class="search-placeholder-msg">Buscando portadas en la web...</div>';
    
    try {
      const results = await apiPost('/api/search_covers', { query });
      coverResultsGrid.innerHTML = '';

      if (!results || results.length === 0) {
        coverResultsGrid.innerHTML = '<div class="search-placeholder-msg">No se encontraron portadas para esa búsqueda.</div>';
        return;
      }

      results.forEach(res => {
        const item = document.createElement('div');
        item.className = 'cover-item-card';
        item.innerHTML = `
          <img src="${res.thumb}" alt="Portada">
          <div class="cover-item-info">
            <div class="cover-item-title">${escapeHtml(res.title)}</div>
            <div class="cover-item-artist">${escapeHtml(res.artist)}</div>
          </div>
        `;
        item.addEventListener('click', async () => {
          coverSearchModal.classList.add('hidden');
          const setRes = await apiPost('/api/set_cover_url', { url: res.url });
          if (setRes && setRes.success) {
            coverImg.src = setRes.preview;
            metaSourceTag.textContent = `Portada Web: ${res.source}`;
          }
        });
        coverResultsGrid.appendChild(item);
      });

      // Add a "Search in Google Images" fallback button at the end
      const googleBtn = document.createElement('div');
      googleBtn.className = 'cover-item-card';
      googleBtn.style.display = 'flex';
      googleBtn.style.flexDirection = 'column';
      googleBtn.style.justifyContent = 'center';
      googleBtn.style.alignItems = 'center';
      googleBtn.style.padding = '20px';
      googleBtn.style.textAlign = 'center';
      googleBtn.innerHTML = `
        <div style="font-size: 2rem; margin-bottom: 10px;">🌐</div>
        <div class="cover-item-title">Buscar en Google Images</div>
        <div class="cover-item-artist" style="margin-top: 5px;">Se abrirá en tu navegador web</div>
      `;
      googleBtn.addEventListener('click', () => {
        window.open('https://www.google.com/search?tbm=isch&q=' + encodeURIComponent(query), '_blank');
      });
      coverResultsGrid.appendChild(googleBtn);

    } catch (err) {
      console.error("Error searching cover online:", err);
      coverResultsGrid.innerHTML = '<div class="search-placeholder-msg">Error al buscar portadas.</div>';
    }
  }

  // ── Full Album & Track Search ─────────────────────────
  btnOpenAlbumSearch.addEventListener('click', () => {
    albumSearchModal.classList.remove('hidden');
    let qArtist = inputArtist.value.trim() === 'Artista Desconocido' ? '' : inputArtist.value.trim();
    let qAlbum = inputAlbum.value.trim().startsWith('Álbum CD (') ? '' : inputAlbum.value.trim();
    const query = `${qArtist} ${qAlbum}`.trim();
    albumSearchInput.value = query;
    if (query) {
      executeAlbumSearch(query);
    }
  });

  btnCloseAlbumModal.addEventListener('click', () => {
    albumSearchModal.classList.add('hidden');
  });

  btnExecuteAlbumSearch.addEventListener('click', () => {
    executeAlbumSearch(albumSearchInput.value);
  });

  albumSearchInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      executeAlbumSearch(albumSearchInput.value);
    }
  });

  async function executeAlbumSearch(query) {
    if (!query.trim()) return;
    albumResultsList.innerHTML = '<div class="search-placeholder-msg">Buscando álbumes y nombres de pistas en la web...</div>';

    try {
      const albums = await apiPost('/api/search_albums', { query });
      albumResultsList.innerHTML = '';

      if (!albums || albums.length === 0) {
        albumResultsList.innerHTML = '<div class="search-placeholder-msg">No se encontraron álbumes en internet.</div>';
        return;
      }

      albums.forEach(alb => {
        const item = document.createElement('div');
        item.className = 'album-item-card';
        const displayTrackCount = alb.tracks && alb.tracks.length > 0 ? alb.tracks.length : alb.track_count || 0;
        item.innerHTML = `
          <img src="${alb.cover_url || "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='50' height='50'><rect width='50' height='50' fill='%23111'/></svg>"}" alt="Carátula">
          <div class="album-item-meta">
            <div class="album-item-title">${escapeHtml(alb.album)} (${alb.year || '----'})</div>
            <div class="album-item-artist">${escapeHtml(alb.artist)} • ${escapeHtml(alb.genre || 'Audio')}</div>
            <div class="album-item-tracks-count">${displayTrackCount} Pistas en el álbum (${alb.source})</div>
          </div>
          <button class="btn-primary-sm btn-import-album">Importar Metadatos</button>
        `;

        item.querySelector('.btn-import-album').addEventListener('click', async () => {
          albumSearchModal.classList.add('hidden');
          
          inputAlbum.value = alb.album || '';
          inputArtist.value = alb.artist || '';
          inputYear.value = alb.year || '';
          inputGenre.value = alb.genre || '';

          if (alb.cover_url) {
            const setRes = await apiPost('/api/set_cover_url', { url: alb.cover_url });
            if (setRes && setRes.success) {
              coverImg.src = setRes.preview;
            }
          }

          if (alb.tracks && alb.tracks.length > 0) {
            alb.tracks.forEach((webTr, i) => {
              if (i < currentTracks.length) {
                currentTracks[i].title = webTr.title;
                currentTracks[i].artist = webTr.artist || alb.artist || '';
              }
            });
            renderTracksTable();
          }

          metaSourceTag.textContent = `Web: ${alb.source}`;
        });

        albumResultsList.appendChild(item);
      });
    } catch (err) {
      console.error("Error searching albums online:", err);
      albumResultsList.innerHTML = '<div class="search-placeholder-msg">Error al buscar álbumes.</div>';
    }
  }

  // ── Ko-fi ─────────────────────────────────────────────
  btnKofi.addEventListener('click', () => {
    window.open('https://ko-fi.com/aolabs', '_blank');
  });

  // ── Start Rip Process ─────────────────────────────────
  btnStartRip.addEventListener('click', async () => {
    const driveLetter = driveSelect.value;
    if (!driveLetter) {
      alert("Por favor selecciona una unidad de CD con disco.");
      return;
    }

    const selectedTracks = currentTracks.filter(t => t.selected);
    if (selectedTracks.length === 0) {
      alert("Por favor selecciona al menos una pista para extraer.");
      return;
    }

    const albumMeta = {
      album: inputAlbum.value.trim() || "Álbum Desconocido",
      artist: inputArtist.value.trim() || "Artista Desconocido",
      year: inputYear.value.trim(),
      genre: inputGenre.value.trim()
    };

    const outputDir = outputPathInput.value.trim();
    const qualitySetting = qualitySelect.value;

    progressModal.classList.remove('hidden');
    progressTitle.textContent = `Extrayendo CD a ${currentFormat.toUpperCase()}...`;
    progressBarFill.style.width = '0%';
    progressPercentageText.textContent = '0%';
    progressStatusText.textContent = 'Iniciando proceso...';
    btnCancelRip.classList.remove('hidden');
    btnAcceptRip.classList.add('hidden');

    try {
      const res = await apiPost('/api/start_rip', {
        drive: driveLetter,
        output_dir: outputDir,
        format: currentFormat,
        quality: qualitySetting,
        album_meta: albumMeta,
        tracks: currentTracks
      });
      if (!res.success) {
        alert(res.message);
        progressModal.classList.add('hidden');
        return;
      }

      // Poll progress
      pollRipProgress();

    } catch (err) {
      console.error("Error starting rip:", err);
      alert("Error al iniciar la extracción.");
      progressModal.classList.add('hidden');
    }
  });

  function pollRipProgress() {
    const interval = setInterval(async () => {
      try {
        const prog = await apiGet('/api/rip_progress');
        progressBarFill.style.width = `${prog.pct}%`;
        progressPercentageText.textContent = `${prog.pct}%`;
        progressStatusText.textContent = prog.status;

        if (prog.done) {
          clearInterval(interval);
          if (prog.success) {
            progressTitle.textContent = "¡Extracción completada con éxito!";
            progressStatusText.textContent = `Archivos guardados en: ${prog.detail}`;
            btnCancelRip.classList.add('hidden');
            btnAcceptRip.classList.remove('hidden');
            
            if (checkAutoOpen.checked) {
              apiPost('/api/open_folder', { path: prog.detail });
            }
          } else {
            progressTitle.textContent = "Error durante la extracción";
            progressStatusText.textContent = prog.detail;
            btnCancelRip.classList.add('hidden');
            btnAcceptRip.classList.remove('hidden');
          }
        }
      } catch (err) {
        clearInterval(interval);
        progressModal.classList.add('hidden');
      }
    }, 1000);
  }

  btnCancelRip.addEventListener('click', async () => {
    await apiPost('/api/cancel_rip');
    progressModal.classList.add('hidden');
  });
  
  btnAcceptRip.addEventListener('click', () => {
    progressModal.classList.add('hidden');
  });

  // Global ESC key listener to close modals
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      if (!coverSearchModal.classList.contains('hidden')) coverSearchModal.classList.add('hidden');
      if (!albumSearchModal.classList.contains('hidden')) albumSearchModal.classList.add('hidden');
    }
  });

  // ── Stop CD audio when tab is closed or navigated away ──
  window.addEventListener('beforeunload', () => {
    // sendBeacon is fire-and-forget — works even during page unload
    navigator.sendBeacon('/api/page_unload', '{}');
  });

  window.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'hidden') {
      navigator.sendBeacon('/api/page_unload', '{}');
    }
  });

  // ── Drive physical removal & insertion polling ────────
  let lastDriveState = true;

  setInterval(async () => {
    const drive = driveSelect.value;
    if (!drive) return;
    
    try {
      const res = await apiPost('/api/check_drive', { drive: drive });
      const isReadyNow = res && res.ready;
      const hasTracksUI = currentTracks.length > 0;

      if (!isReadyNow && hasTracksUI) {
        // El disco fue extraído físicamente
        console.log("[app.js] El disco fue retirado manualmente. Limpiando interfaz...");
        statusText.textContent = "El disco fue retirado.";
        metaSourceTag.textContent = "No se detectaron los metadatos automáticamente";
        inputAlbum.value = "";
        inputArtist.value = "";
        inputYear.value = "";
        inputGenre.value = "";
        coverImg.src = "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='300' height='300' viewBox='0 0 24 24' fill='none' stroke='%233a4161' stroke-width='1.5'><rect x='3' y='3' width='18' height='18' rx='2'/><circle cx='12' cy='12' r='4'/><path d='M12 2v4M12 18v4M2 12h4M18 12h4'/></svg>";
        
        currentTracks = [];
        renderTracksTable();
        lastDriveState = false;
      } 
      else if (isReadyNow && !hasTracksUI && !lastDriveState) {
        // Un nuevo disco fue insertado
        console.log("[app.js] Nuevo disco detectado. Cargando automáticamente...");
        lastDriveState = true;
        onDriveSelected(drive);
      }
      else {
        lastDriveState = isReadyNow;
      }
    } catch (e) {
      // Ignorar errores de red
    }
  }, 2000);

  console.log('[app.js] Initialization complete ✅');
});
