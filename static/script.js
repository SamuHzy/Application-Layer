(function(){
  "use strict";

  // ---------- utility ----------
  function pad(n,l){l=l||2;return String(n).padStart(l,'0');}
  function nowStamp(){
    var d = new Date();
    return pad(d.getHours())+':'+pad(d.getMinutes())+':'+pad(d.getSeconds())+'.'+pad(d.getMilliseconds(),3);
  }
  function escHtml(s){
    return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
  }
  // The backend marks highlighted fragments as [[text]] (primary) or
  // [[s:text]] (secondary/server-emphasis). Escape everything first,
  // then turn those markers into <span> highlights.
  function renderDetail(raw){
    var escaped = escHtml(raw);
    return escaped.replace(/\[\[(s:)?([^\]]*)\]\]/g, function(_, sflag, inner){
      return '<span class="hl' + (sflag ? ' s' : '') + '">' + inner + '</span>';
    });
  }

  var clockEl = document.getElementById('clock');
  setInterval(function(){ clockEl.textContent = nowStamp(); }, 97);

  // ---------- activity log ----------
  var logEl = document.getElementById('activity-log');
  function logActivity(msg){
    if(logEl.querySelector('.log-empty')) logEl.innerHTML = '';
    var row = document.createElement('div');
    row.className = 'log-entry';
    row.innerHTML = '<span class="t">'+nowStamp()+'</span><span class="m">'+escHtml(msg)+'</span>';
    logEl.appendChild(row);
    logEl.scrollTop = logEl.scrollHeight;
  }

  var statusEl = document.getElementById('status-line');
  function setStatus(text, active){
    statusEl.textContent = text;
    statusEl.classList.toggle('idle', !active);
  }

  // ---------- tab switching ----------
  var tabs = document.querySelectorAll('.tab');
  var panels = { browse:'panel-browse', mail:'panel-mail', stream:'panel-stream' };
  tabs.forEach(function(t){
    t.addEventListener('click', function(){
      tabs.forEach(function(x){x.classList.remove('active');});
      t.classList.add('active');
      Object.keys(panels).forEach(function(k){
        document.getElementById(panels[k]).style.display = (k===t.dataset.mode)?'flex':'none';
      });
      setStatus('idle — choose an activity and run it', false);
    });
  });

  // ================= VISUALIZER ENGINE =================
  var timelineEl = document.getElementById('timeline');
  var emptyVizEl = document.getElementById('empty-viz');
  var vizControls = document.getElementById('viz-controls');
  var overallProgress = document.getElementById('overall-progress');
  var overallProgressFill = document.getElementById('overall-progress-fill');
  var stepCounterEl = document.getElementById('step-counter');
  var prevBtn = document.getElementById('prev-btn');
  var nextBtn = document.getElementById('next-btn');
  var playPauseBtn = document.getElementById('playpause-btn');
  var replayBtn = document.getElementById('replay-btn');
  var filterBtns = document.querySelectorAll('#layer-filter .filter-btn');
  var countAllEl = document.getElementById('count-all');
  var countL7El = document.getElementById('count-l7');
  var countL4El = document.getElementById('count-l4');

  var fullSequence = [];
  var sequence = [];
  var activeLayer = 'all';
  var currentIndex = -1;
  var playing = false;
  var timer = null;
  var STEP_MS = 650;

  function stepLayer(step){
    if(step.layer) return step.layer;
    return (step.proto === 'TCP' || step.proto === 'UDP') ? 'L4' : 'L7';
  }

  function updateLayerCounts(){
    var l7 = 0, l4 = 0;
    fullSequence.forEach(function(s){
      if(stepLayer(s) === 'L4') l4++;
      else l7++;
    });
    if(countAllEl) countAllEl.textContent = fullSequence.length;
    if(countL7El) countL7El.textContent = l7;
    if(countL4El) countL4El.textContent = l4;
  }

  function applyLayerFilter(revealAll){
    if(activeLayer === 'all'){
      sequence = fullSequence.slice();
    } else {
      sequence = fullSequence.filter(function(s){ return stepLayer(s) === activeLayer; });
    }
    renderTimeline();
    if(revealAll){
      currentIndex = sequence.length - 1;
    } else if(currentIndex >= sequence.length){
      currentIndex = sequence.length - 1;
    }
    updateUiForIndex();
  }

  filterBtns.forEach(function(btn){
    btn.addEventListener('click', function(){
      filterBtns.forEach(function(b){ b.classList.remove('active'); });
      btn.classList.add('active');
      activeLayer = btn.dataset.layer || 'all';
      if(fullSequence.length > 0){
        var wasPlaying = playing;
        stopPlaying();
        // If playback had already started or finished, reveal matching steps immediately
        applyLayerFilter(!wasPlaying && currentIndex >= 0);
        if(wasPlaying){
          currentIndex = -1;
          updateUiForIndex();
          startPlaying();
        }
      }
    });
  });

  function dirColor(dir){ return dir==='c2s' ? 'var(--c2s)' : 'var(--s2c)'; }
  function dirLabel(dir){ return dir==='c2s' ? 'client → server' : 'server → client'; }

  function renderTimeline(){
    timelineEl.innerHTML = '';
    sequence.forEach(function(step, i){
      var layer = stepLayer(step);
      var layerClass = layer.toLowerCase();
      var layerBadgeText = layer === 'L4' ? 'L4 TRANSPORT' : 'L7 APP';
      var wrap = document.createElement('div');
      wrap.className = 'step layer-' + layerClass;
      wrap.style.setProperty('--dir-color', dirColor(step.dir));
      wrap.id = 'step-'+i;
      wrap.innerHTML =
        '<div class="step-row">'+
          '<div class="rail"><div class="node"></div><div class="connector"></div></div>'+
          '<div class="msg-card">'+
            '<div class="msg-meta">'+
              '<div class="msg-badges">'+
                '<span class="msg-layer '+layerClass+'">'+layerBadgeText+'</span>'+
                '<span class="msg-proto">'+escHtml(step.proto)+'</span>'+
              '</div>'+
              '<span class="msg-dir">'+(step.dir==='c2s'?'→':'←')+' '+dirLabel(step.dir)+'</span>'+
              '<span class="msg-time">t + '+step.time+'ms</span>'+
            '</div>'+
            '<div class="msg-summary">'+escHtml(step.summary)+'</div>'+
            '<div class="msg-detail">'+renderDetail(step.detail)+'</div>'+
          '</div>'+
        '</div>';
      timelineEl.appendChild(wrap);
    });
  }

  function updateUiForIndex(){
    document.querySelectorAll('.step').forEach(function(el, i){
      el.classList.toggle('revealed', i<=currentIndex);
      el.classList.toggle('current', i===currentIndex);
    });
    var shown = sequence.length ? (currentIndex+1) : 0;
    stepCounterEl.textContent = shown+' / '+sequence.length;
    var pct = sequence.length ? (shown/sequence.length*100) : 0;
    overallProgressFill.style.width = pct+'%';
    prevBtn.disabled = currentIndex<=0;
    nextBtn.disabled = currentIndex>=sequence.length-1;
    if(currentIndex>=0){
      var el = document.getElementById('step-'+currentIndex);
      if(el) el.scrollIntoView({block:'nearest', behavior:'smooth'});
    }
    if(currentIndex >= sequence.length-1){
      stopPlaying();
    }
  }

  function stepForward(){
    if(currentIndex < sequence.length-1){ currentIndex++; updateUiForIndex(); }
  }
  function stepBackward(){
    if(currentIndex > 0){ currentIndex--; updateUiForIndex(); }
  }
  function startPlaying(){
    if(sequence.length===0) return;
    if(currentIndex>=sequence.length-1) currentIndex=-1;
    playing = true;
    playPauseBtn.textContent = '⏸ Pause';
    tick();
  }
  function tick(){
    clearTimeout(timer);
    if(!playing) return;
    stepForward();
    if(currentIndex < sequence.length-1){
      timer = setTimeout(tick, STEP_MS);
    } else {
      stopPlaying();
    }
  }
  function stopPlaying(){
    playing = false;
    clearTimeout(timer);
    playPauseBtn.textContent = '▶ Play';
  }
  function togglePlay(){ playing ? stopPlaying() : startPlaying(); }
  function replay(){
    stopPlaying();
    currentIndex = -1;
    updateUiForIndex();
    startPlaying();
  }

  prevBtn.addEventListener('click', function(){ stopPlaying(); stepBackward(); });
  nextBtn.addEventListener('click', function(){ stopPlaying(); stepForward(); });
  playPauseBtn.addEventListener('click', togglePlay);
  replayBtn.addEventListener('click', replay);

  function loadSequence(seq, statusText){
    stopPlaying();
    fullSequence = seq || [];
    updateLayerCounts();
    currentIndex = -1;
    emptyVizEl.style.display = 'none';
    timelineEl.style.display = 'flex';
    vizControls.style.display = 'flex';
    overallProgress.style.display = 'block';
    applyLayerFilter(false);
    setStatus(statusText, true);
    startPlaying();
  }

  // ================= CALL THE FLASK BACKEND =================
  function postJSON(url, payload){
    return fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    }).then(function(res){
      if(!res.ok) throw new Error('request failed: ' + res.status);
      return res.json();
    });
  }

  document.getElementById('visit-btn').addEventListener('click', function(){
    var url = document.getElementById('url-input').value.trim() || 'www.example.com/';
    setStatus('contacting server …', true);
    postJSON('/api/browse', { url: url }).then(function(data){
      logActivity('Visited '+url);
      loadSequence(data.sequence, data.status);
    }).catch(function(err){ setStatus('error: '+err.message, false); });
  });

  document.getElementById('send-btn').addEventListener('click', function(){
    var to = document.getElementById('mail-to').value.trim() || '[email protected]';
    var subject = document.getElementById('mail-subject').value.trim() || '(no subject)';
    var body = document.getElementById('mail-body').value.trim() || '';
    setStatus('contacting server …', true);
    postJSON('/api/mail', { to: to, subject: subject, body: body }).then(function(data){
      logActivity('Sent mail to '+to+' — "'+subject+'"');
      loadSequence(data.sequence, data.status);
    }).catch(function(err){ setStatus('error: '+err.message, false); });
  });

  var playerLabel = document.getElementById('player-label');
  var playerBar = document.getElementById('player-bar');
  var playBtn = document.getElementById('play-btn');
  var pauseBtn = document.getElementById('pause-btn');
  var qualitySelect = document.getElementById('quality-select');
  var streamPlaying = false;
  var barTimer = null;

  function requestStream(url, quality, statusPrefix){
    setStatus('contacting server …', true);
    return postJSON('/api/stream', { url: url, quality: quality }).then(function(data){
      loadSequence(data.sequence, data.status);
    }).catch(function(err){ setStatus('error: '+err.message, false); });
  }

  playBtn.addEventListener('click', function(){
    var url = document.getElementById('stream-url').value.trim() || 'video.example.com/stream';
    var quality = qualitySelect.value;
    streamPlaying = true;
    playBtn.disabled = true; pauseBtn.disabled = false;
    playerLabel.textContent = 'playing — '+quality;
    logActivity('Started stream '+url+' at '+quality);
    requestStream(url, quality);
    animateBar();
  });
  pauseBtn.addEventListener('click', function(){
    streamPlaying = false;
    playBtn.disabled = false; pauseBtn.disabled = true;
    playerLabel.textContent = 'paused';
    logActivity('Paused stream');
    stopPlaying();
    clearInterval(barTimer);
  });
  qualitySelect.addEventListener('change', function(){
    if(streamPlaying){
      var url = document.getElementById('stream-url').value.trim() || 'video.example.com/stream';
      logActivity('Switched quality to '+qualitySelect.value);
      requestStream(url, qualitySelect.value);
    }
  });
  function animateBar(){
    var pct = 0;
    clearInterval(barTimer);
    barTimer = setInterval(function(){
      if(!streamPlaying){ return; }
      pct = (pct+1.2) % 100;
      playerBar.style.width = pct+'%';
    }, 120);
  }

})();
