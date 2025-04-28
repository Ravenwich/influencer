// static/js/socket_handlers.js

let profiles = [];
let editingIndex = null;
let newProfilePending = false;
let selectedIndex = 0;

const socket = io();

// map plural section titles to their singular form
const singularMap = {
    'Biases': 'Bias',
    'Strengths': 'Strength',
    'Weaknesses': 'Weakness',
    'Influence Skills': 'Influence Skill'
  };
  

// Live update handler
socket.on('profiles_updated', (newProfiles) => {
    profiles = newProfiles;
    if (newProfilePending) {
      editingIndex = profiles.length - 1;
      newProfilePending = false;
    }
    renderSidebar();
    renderDetail();
  });
  

// Create a new blank profile
function createNewProfile() {
    const blank = {
        name: '',
        appearance: '',
        background: '',
        personality: '',
        attitude: '',
        goal: '',
        benefit: '',
        special: '',
        influence_successes: 0,
        successes_needed: 1,
        biases: [{ text: '', revealed: false }],
        strengths: [{ text: '', revealed: false }],
        weaknesses: [{ text: '', revealed: false }],
        influence_skills: [{ text: '', revealed: false }],
        photoUrl: '/static/images/default.png'
    };
    newProfilePending = true;
    socket.emit('create_profile', blank);
}

function sanitize(text) {
    return text.replace(/<[^>]*>/g, '').trim();
  }

// Delete a profile with confirmation
function deleteProfile(idx) {
    if (confirm("Are you sure you want to delete this profile?")) {
        socket.emit('delete_profile', { index: idx });
    }
}

// Toggle reveal/hide for list items
function toggleReveal(profileIdx, category, itemIdx) {
    const item = profiles[profileIdx][category][itemIdx];
    item.revealed = !item.revealed;
    socket.emit('update_profile', { index: profileIdx, profile: profiles[profileIdx] });
}

// Increment influence on Gretchen page
function incrementInfluence(profileIdx) {
    profiles[profileIdx].influence_successes += 1;
    socket.emit('update_profile', { index: profileIdx, profile: profiles[profileIdx] });
}

// Reset influence successes to zero
function resetInfluence(profileIdx) {
    profiles[profileIdx].influence_successes = 0;
    socket.emit('update_profile', { index: profileIdx, profile: profiles[profileIdx] });
}

// Renders the sidebar list of profiles
function renderSidebar() {
    const list = document.getElementById('sidebar-list');
    list.innerHTML = '';
    profiles.forEach((p, i) => {
        const item = document.createElement('div');
        item.className = 'item' + (i === selectedIndex ? ' active' : '');
        item.textContent = p.name || 'Untitled';
        item.onclick = () => {
            selectedIndex = i;
            editingIndex = null;
            renderSidebar();
            renderDetail();
        };
        list.appendChild(item);
    });
}

function renderDetail() {
    // Always pull the true mode from the HTML page
    const gretchenMode = Boolean(window.IS_GRETCHEN);
  
    const container = document.getElementById('profile-detail');
    const idx = selectedIndex;
    const contentHTML = (gretchenMode && editingIndex === idx)
      ? renderEditForm(profiles[idx], idx)
      : renderView(profiles[idx], idx, gretchenMode);
  
    container.innerHTML = `<div class="detail-card">${contentHTML}</div>`;
  }
  

// Non-edit view with two-pane ID-card style
function renderView(profile, idx, gretchenMode) {
    let html = `
    <div class="profile-header">
      <img src="${profile.photoUrl || '/static/images/default.png'}" alt="${profile.name}" />
      <h2>${profile.name}</h2>
    </div>
    <div class="profile-body">
      <div class="profile-section">
        <h3>Overview</h3>
            ${renderField("Appearance", profile.appearance)}
            ${renderField("Background", profile.background)}
            ${renderField("Personality", profile.personality)}
            ${gretchenMode ? renderField("Attitude", profile.attitude) : ""}
            ${gretchenMode ? renderField("Goal", profile.goal) : ""}
            ${gretchenMode ? renderField("Benefit", profile.benefit) : ""}
            ${gretchenMode ? renderField("Special", profile.special) : ""}
      </div>

      <div class="profile-section">
        <h3>Stats & Traits</h3>
        <div class="influence-controls">
  <span><strong>Influence:</strong> ${profile.influence_successes}${gretchenMode 
      ? '/' + profile.successes_needed 
      : ''}</span>
  ${gretchenMode ? `
    <button class="edit" onclick="incrementInfluence(${idx})">
  <i class="fa-solid fa-heart-circle-plus"></i> +1
</button>
<button class="delete" onclick="resetInfluence(${idx})">
  <i class="fa-solid fa-arrow-rotate-left"></i> Reset
</button>

  ` : ''}
</div>

        ${renderList("Biases", profile.biases, idx, gretchenMode)}
        ${renderList("Strengths", profile.strengths, idx, gretchenMode)}
        ${renderList("Weaknesses", profile.weaknesses, idx, gretchenMode)}
        ${renderList("Influence Skills", profile.influence_skills, idx, gretchenMode)}
      </div>
    </div>
  `;

    if (gretchenMode && editingIndex !== idx) {
        html += `
      <div style="padding:24px; text-align:right;">
        <button class="edit" onclick="startEditProfile(${idx})">
  <i class="fa-solid fa-pen-nib"></i>Edit
</button>
<button class="delete" onclick="deleteProfile(${idx})">
  <i class="fa-solid fa-x"></i> Delete
</button>

      </div>
    `;
    }
    return html;
}

// Simple field renderer
function renderField(label, value) {
    return `<p><strong>${label}:</strong> ${value}</p>`;
}

// List renderer (edit, Gretchen-view, and player modes)
function renderList(label, items, profileIdx, gretchenMode) {
    const inEdit = gretchenMode && editingIndex === profileIdx;
    const category = label.toLowerCase().replace(/ /g, '_');
    if (!items.length && !inEdit) return '';

    let html = `<p><strong>${label}:</strong></p><ul>`;

    if (inEdit) {
        items.forEach((item, i) => {
            const text = item.text || '';
            html += `<li>
              <input type="text" id="edit-${category}-${i}" value="${text}" style="width:70%;" />
              <button onclick="removeListItem(${profileIdx}, '${category}', ${i})">✖️</button>
            </li>`;
        });
        const singular = singularMap[label] || label.replace(/s$/, '');
        html += `
        <li>
          <button class="add" onclick="addListItem(${profileIdx}, '${category}')">
  <i class="fa-solid fa-plus"></i>Add ${singular}
</button>

        </li>`;
    

    } else if (gretchenMode) {
        items.forEach((item, i) => {
            const revealed = item.revealed;
            html += `<li>${item.text} <label class="switch">
                <input type="checkbox" ${revealed ? 'checked' : ''}
                    onchange="toggleReveal(${profileIdx}, '${category}', ${i})" />
                <span class="slider"></span>
              </label></li>`;
        });

    } else {
        let hiddenExists = false;
        items.forEach(item => {
            if (item.revealed) {
                html += `<li>${item.text}</li>`;
            } else {
                hiddenExists = true;
            }
        });
        if (hiddenExists) html += `<li>???</li>`;
    }

    html += `</ul>`;
    return html;
}

/**
 * Copy every current edit‑form input back into profiles[profileIdx]
 * so that re‑rendering the form preserves what you've typed so far.
 */
function updateDraftFromForm(profileIdx) {
    const p = profiles[profileIdx];
    // simple fields
    ['name','appearance','background','personality','attitude','goal','benefit','special']
      .forEach(key => {
        const el = document.getElementById(`edit-${key}`);
        if (el) p[key] = el.value;
      });
    // numeric fields
    ['influence_successes','successes_needed']
      .forEach(key => {
        const el = document.getElementById(`edit-${key}`);
        if (el) p[key] = parseInt(el.value, 10) || 0;
      });
    // list fields
    ['biases','strengths','weaknesses','influence_skills']
      .forEach(category => {
        profiles[profileIdx][category] = profiles[profileIdx][category]
          .map((item, i) => {
            const inp = document.getElementById(`edit-${category}-${i}`);
            return {
              text: inp ? inp.value : item.text,
              revealed: item.revealed
            };
          });
      });
  }  

// Add/remove helpers (new items hidden by default)
function addListItem(profileIdx, category) {
    // save draft before mutating
    updateDraftFromForm(profileIdx);
    // add new hidden‑by‑default entry
    profiles[profileIdx][category].push({ text: '', revealed: false });
    renderDetail();
  }
  
  function removeListItem(profileIdx, category, itemIdx) {
    updateDraftFromForm(profileIdx);
    profiles[profileIdx][category].splice(itemIdx, 1);
    renderDetail();
  }
  

  function renderEditForm(p, idx) {
    return `
    <div class="edit-form">
      <h2>Editing: ${p.name || 'New Profile'}</h2>
  
      <!-- Core fields wrapped in two cards -->
      <div class="edit-lists">
        <!-- Left card -->
        <div class="edit-list">
          <div class="field-group">
            ${fieldInput("Name", "name", p.name)}
            ${fieldInput("Attitude", "attitude", p.attitude, true)}
            ${fieldInput("Goal", "goal", p.goal, true)}
            ${fieldInput("Benefit", "benefit", p.benefit, true)}
            ${fieldInput("Special", "special", p.special, true)}
          </div>
        </div>
  
        <!-- Right card -->
        <div class="edit-list">
          <div class="field-group">
            ${fieldInput("Appearance", "appearance", p.appearance, true)}
            ${fieldInput("Background", "background", p.background, true)}
            ${fieldInput("Personality", "personality", p.personality, true)}
            ${fieldInput("Influence Successes", "influence_successes", p.influence_successes)}
            ${fieldInput("Successes Needed", "successes_needed", p.successes_needed)}
          </div>
        </div>
      </div>
  
      <!-- Existing list cards -->
      <div class="edit-lists">
        <div class="edit-list">
          <h3>Biases</h3>
          ${renderList("Biases", p.biases, idx, true)}
        </div>
        <div class="edit-list">
          <h3>Strengths</h3>
          ${renderList("Strengths", p.strengths, idx, true)}
        </div>
        <div class="edit-list">
          <h3>Weaknesses</h3>
          ${renderList("Weaknesses", p.weaknesses, idx, true)}
        </div>
        <div class="edit-list">
          <h3>Influence Skills</h3>
          ${renderList("Influence Skills", p.influence_skills, idx, true)}
        </div>
      </div>
  
      <!-- Photo upload remains its own card -->
      <div class="edit-list photo-group">
        <h3>Photo</h3>
        <input type="file" id="edit-photo-file" accept="image/*" />
      </div>
  
      <!-- Action buttons at bottom -->
      <div class="edit-actions">
        <button class="edit" onclick="saveEdits(${idx})">
          <i class="fa-solid fa-check"></i>Save
        </button>
        <button class="delete" onclick="cancelEdit()">
          <i class="fa-solid fa-xmark"></i>Cancel
        </button>
      </div>
    </div>
    `;
  }
  
  

// Field input helper
function fieldInput(label, key, value, textarea = false) {
    if (textarea) {
        return `
        <p><strong>${label}:</strong><br>
        <textarea id="edit-${key}" rows="2" style="width:100%;">${value}</textarea>
        </p>`;
    }
    return `
    <p><strong>${label}:</strong><br>
    <input id="edit-${key}" type="text" value="${value}" style="width:100%;" />
    </p>`;
}

// Handlers for edit flow
function startEditProfile(idx) {
    editingIndex = idx;
    renderDetail();
}
function cancelEdit() {
    editingIndex = null;
    renderDetail();
}
async function saveEdits(idx) {

let photoUrl = profiles[idx].photoUrl || '/static/images/default.png';
const inputFile = document.getElementById('edit-photo-file');
if (inputFile && inputFile.files.length > 0) {
  // upload to server
  const form = new FormData();
  form.append('photo', inputFile.files[0]);
  const resp = await fetch('/upload_photo', { method: 'POST', body: form });
  const data = await resp.json();
  if (data.driveId) {
    photoUrl = `/images/${data.driveId}`;
  }
}
    const gatherList = category => profiles[idx][category]
        .map((_, i) => {
            const val = document.getElementById(`edit-${category}-${i}`)?.value || '';
            return { text: val, revealed: profiles[idx][category][i].revealed };
        })
        .filter(item => item.text.trim() !== '');
        const getClean = key => sanitize(document.getElementById(`edit-${key}`)?.value || '');

        // Build updated profile
        const updated = {
          name: getClean('name'),
          appearance: getClean('appearance'),
          background: getClean('background'),
          personality: getClean('personality'),
          attitude: getClean('attitude'),
          goal: getClean('goal'),
          benefit: getClean('benefit'),
          special: getClean('special'),
          influence_successes: parseInt(getClean('influence_successes'), 10) || 0,
          successes_needed: parseInt(getClean('successes_needed'), 10) || 0,
      
          // For lists, reuse gatherList but sanitize each text:
          biases: gatherList('biases').map(item => ({
            text: sanitize(item.text),
            revealed: item.revealed
          })),
          strengths: gatherList('strengths').map(item => ({
            text: sanitize(item.text),
            revealed: item.revealed
          })),
          weaknesses: gatherList('weaknesses').map(item => ({
            text: sanitize(item.text),
            revealed: item.revealed
          })),
          influence_skills: gatherList('influence_skills').map(item => ({
            text: sanitize(item.text),
            revealed: item.revealed
          })),
      
          photoUrl: photoUrl
        };
      
        socket.emit('update_profile', { index: idx, profile: updated });
        editingIndex = null;
      }
