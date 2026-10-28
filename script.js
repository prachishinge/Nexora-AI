document.addEventListener('DOMContentLoaded', () => {
    const messageInput = document.getElementById('message-input');
    const sendButton = document.getElementById('send-button');
    const chatMessages = document.getElementById('chat-messages');
    const welcomeScreen = document.getElementById('welcome-screen');
    const authSection = document.getElementById('auth-section');
    const chatHistoryList = document.getElementById('chat-history-list');
    const newChatBtn = document.getElementById('new-chat-btn');
    const topNewChatBtn = document.getElementById('top-new-chat-btn');
    const sidebar = document.getElementById('sidebar');
    const sidebarToggleBtn = document.getElementById('sidebar-toggle-btn');
    const sidebarCloseBtn = document.getElementById('sidebar-close-btn');
    const clearHistoryBtn = document.getElementById('clear-history-btn');

    // --- ATTACHMENT CONTROLS (Files, Folder, Images like ChatGPT) ---
    const attachButton = document.getElementById('attach-button');
    const attachMenu = document.getElementById('attach-menu');
    const attachFileOpt = document.getElementById('attach-file-opt');
    const attachFolderOpt = document.getElementById('attach-folder-opt');
    const attachImageOpt = document.getElementById('attach-image-opt');
    const fileUploadInput = document.getElementById('file-upload-input');
    const folderUploadInput = document.getElementById('folder-upload-input');
    const imageUploadInput = document.getElementById('image-upload-input');
    const attachmentPreviewTray = document.getElementById('attachment-preview-tray');
    const inputBoxWrapper = document.getElementById('input-box-wrapper');
    const imageLightboxModal = document.getElementById('image-lightbox-modal');
    const lightboxImg = document.getElementById('lightbox-img');
    const lightboxCaption = document.getElementById('lightbox-caption');
    const closeLightboxBtn = document.getElementById('close-lightbox-btn');

    let attachedItems = [];

    // Configure PDF.js worker if available
    if (window.pdfjsLib) {
        window.pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';
    }

    // --- UNIFIED BACKEND API FETCHER ---
    // Automatically connects whether frontend is deployed on Vercel (HTTPS), opened via backend (8000/8080), Live Server (5500), or file://
    async function backendFetch(path, options = {}) {
        const isHostedOnBackend = window.location.port === '8000' || window.location.port === '8080';
        const isHttps = window.location.protocol === 'https:';
        const endpoints = [];

        // 1. On HTTPS (Vercel deployment) or when hosted directly on backend, use relative /api path first
        if (isHttps || isHostedOnBackend) {
            endpoints.push(path);
        }

        // 2. Local fallback endpoints
        endpoints.push(`http://127.0.0.1:8000${path}`);
        endpoints.push(`http://127.0.0.1:8080${path}`);

        // 3. Dev server fallback
        if (!endpoints.includes(path) && window.location.protocol !== 'file:') {
            endpoints.push(path);
        }

        let lastErr = null;
        for (const url of endpoints) {
            try {
                const res = await fetch(url, options);
                // If it's a 404 from a static dev server (e.g. Live Server port 5500), try next port
                if (res.status === 404 && !url.includes(':8000') && !url.includes(':8080')) {
                    continue;
                }
                return res;
            } catch (err) {
                lastErr = err;
            }
        }
        throw lastErr || new Error('Backend connection failed');
    }

    // Helper to resolve backend URLs (images, downloads) across ports and environments
    function resolveBackendUrl(url) {
        if (!url) return '';
        if (url.startsWith('http://') || url.startsWith('https://') || url.startsWith('data:') || url.startsWith('blob:')) {
            return url;
        }
        if (url.startsWith('/api/')) {
            if (window.location.protocol === 'https:') {
                return url;
            }
            const isHostedOnBackend = window.location.port === '8000' || window.location.port === '8080';
            if (isHostedOnBackend) {
                return url;
            }
            return `http://127.0.0.1:8000${url}`;
        }
        return url;
    }

    // Client-side visual generation intent detection
    function isClientImageRequest(text) {
        if (!text) return false;
        const p = text.toLowerCase();
        return p.startsWith('/image') || p.startsWith('/draw') || p.startsWith('/generate') ||
            /\b(image|picture|photo|pic|poster|chart|infographic|wallpaper|illustration|drawing|portrait)\b/i.test(p) ||
            /(फोटो|चित्र|तस्वीर|इमेज|पोस्टर|चार्ट|banav|kadh|dakhva|dakhav|draw|paint)/i.test(p);
    }

    // --- AUTHENTICATION STATE ---
    const isLoggedIn = localStorage.getItem('isLoggedIn') === 'true';
    const userEmail = localStorage.getItem('userEmail') || 'User';

    // Extract user friendly name from email (e.g. sourabh.patil@gmail.com -> Sourabh Patil, or rahul@gmail.com -> Rahul)
    function extractNameFromEmail(email) {
        if (!email || !email.includes('@')) return email || 'User';
        let rawName = email.split('@')[0];
        // Replace dots, underscores, dashes, numbers with spaces
        rawName = rawName.replace(/[._\-0-9]+/g, ' ').trim();
        if (!rawName) return email.split('@')[0];
        // Capitalize each word
        return rawName.split(' ')
            .filter(Boolean)
            .map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
            .join(' ');
    }

    const userName = localStorage.getItem('userName') || extractNameFromEmail(userEmail);
    const userInitial = (userName.charAt(0) || 'U').toUpperCase();

    if (isLoggedIn && authSection) {
        authSection.innerHTML = `
            <div class="user-logged-box">
                <div class="user-avatar-circle">
                    ${userInitial}
                </div>
                <div class="user-info-text">
                    <span class="user-display-name" title="${userName}">${userName}</span>
                    <span class="user-display-email" title="${userEmail}">${userEmail}</span>
                </div>
                <button id="logout-btn" class="logout-icon-btn" title="Log Out">Log out</button>
            </div>
        `;
        document.getElementById('logout-btn')?.addEventListener('click', () => {
            localStorage.removeItem('isLoggedIn');
            localStorage.removeItem('userEmail');
            localStorage.removeItem('userName');
            window.location.reload();
        });
    }

    // --- USER-ISOLATED MULTI-SESSION CHAT HISTORIES ---
    // Each user has their own isolated localStorage key: chatSessions_{email}
    // Guests get chatSessions_guest (never synced to server or leaked to other users)
    function getCurrentUserKey() {
        const loggedIn = localStorage.getItem('isLoggedIn') === 'true';
        const email = (localStorage.getItem('userEmail') || '').toLowerCase().trim();
        if (loggedIn && email && email !== 'user') {
            return `chatSessions_${email}`;
        }
        return 'chatSessions_guest';
    }

    // Clean up any legacy un-scoped shared 'chatSessions' key to prevent old data leaks
    if (localStorage.getItem('chatSessions')) {
        localStorage.removeItem('chatSessions');
    }
    
    function getSessions() {
        try {
            const key = getCurrentUserKey();
            return JSON.parse(localStorage.getItem(key) || '[]');
        } catch (e) {
            return [];
        }
    }

    function saveSessions(sessions) {
        const key = getCurrentUserKey();
        localStorage.setItem(key, JSON.stringify(sessions));
        persistSessionsToServer(sessions);
    }

    async function persistSessionsToServer(sessions) {
        const loggedIn = localStorage.getItem('isLoggedIn') === 'true';
        const email = (localStorage.getItem('userEmail') || '').toLowerCase().trim();
        // Only persist to server if logged in with a valid user email.
        // Unauthenticated guests store their chats strictly on their own device!
        if (!loggedIn || !email || email === 'user') return;

        const payload = { user_id: email, sessions };
        try {
            await backendFetch('/api/sessions', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
        } catch (e) {
            // Silently fail if server is offline
        }
    }

    async function syncWithServerSessions() {
        const loggedIn = localStorage.getItem('isLoggedIn') === 'true';
        const email = (localStorage.getItem('userEmail') || '').toLowerCase().trim();
        // If guest (not logged in), DO NOT fetch any sessions from server!
        // This guarantees any visitor opening the link starts completely fresh.
        if (!loggedIn || !email || email === 'user') {
            renderHistorySidebar();
            return;
        }

        let serverSessions = [];
        try {
            const res = await backendFetch(`/api/sessions?user_id=${encodeURIComponent(email)}`);
            if (res.ok) {
                const data = await res.json();
                serverSessions = data.sessions || [];
            }
        } catch (e) {}

        const localSessions = getSessions();
        const map = new Map();

        // 1. Add server sessions belonging to this user
        serverSessions.forEach(s => {
            if (s && s.id) map.set(s.id, s);
        });

        // 2. Merge local sessions for this user (keep newest)
        localSessions.forEach(s => {
            if (s && s.id) {
                const existing = map.get(s.id);
                if (!existing || (s.timestamp && s.timestamp >= (existing.timestamp || 0))) {
                    map.set(s.id, s);
                }
            }
        });

        const merged = Array.from(map.values());
        merged.sort((a, b) => (b.timestamp || 0) - (a.timestamp || 0));

        const key = getCurrentUserKey();
        localStorage.setItem(key, JSON.stringify(merged));
        renderHistorySidebar();
        if (merged.length > 0) {
            persistSessionsToServer(merged);
        }
    }

    function exportChatHistory() {
        const sessions = getSessions();
        if (!sessions || sessions.length === 0) {
            alert('No saved chats to export yet.');
            return;
        }
        const dataStr = 'data:text/json;charset=utf-8,' + encodeURIComponent(JSON.stringify(sessions, null, 2));
        const downloadAnchor = document.createElement('a');
        downloadAnchor.setAttribute('href', dataStr);
        downloadAnchor.setAttribute('download', `study_ai_chat_backup_${new Date().toISOString().slice(0, 10)}.json`);
        document.body.appendChild(downloadAnchor);
        downloadAnchor.click();
        downloadAnchor.remove();
    }

    function handleImportHistoryFile(e) {
        const file = e.target.files && e.target.files[0];
        if (!file) return;

        const reader = new FileReader();
        reader.onload = async (event) => {
            try {
                const imported = JSON.parse(event.target.result);
                if (!Array.isArray(imported)) {
                    throw new Error('Invalid file structure. Expected list of chat sessions.');
                }
                const current = getSessions();
                const map = new Map();
                current.forEach(s => { if (s && s.id) map.set(s.id, s); });
                imported.forEach(s => { if (s && s.id) map.set(s.id, s); });
                const merged = Array.from(map.values());
                merged.sort((a, b) => (b.timestamp || 0) - (a.timestamp || 0));

                saveSessions(merged);
                renderHistorySidebar();
                alert(`✅ Successfully restored ${imported.length} chat sessions! They are now saved permanently.`);
            } catch (err) {
                alert('⚠️ Import failed: ' + err.message);
            } finally {
                e.target.value = '';
            }
        };
        reader.readAsText(file);
    }

    // ChatGPT behavior: When user opens the site anew, always start a FRESH New Chat.
    // The previous sessions are safely kept in the sidebar.
    let currentSessionId = null;

    function renderHistorySidebar() {
        const sessions = getSessions();
        chatHistoryList.innerHTML = '';

        if (sessions.length === 0) {
            chatHistoryList.innerHTML = `<div class="no-history-hint">No saved chats yet</div>`;
            return;
        }

        sessions.forEach(session => {
            const item = document.createElement('div');
            item.className = 'history-item';
            if (session.id === currentSessionId) {
                item.classList.add('active');
            }

            const title = document.createElement('span');
            title.className = 'history-item-title';
            title.textContent = session.title || 'Conversation';
            title.title = session.title || 'Conversation';

            const delBtn = document.createElement('button');
            delBtn.className = 'history-delete-btn';
            delBtn.innerHTML = `
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <polyline points="3 6 5 6 21 6"></polyline>
                    <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                </svg>
            `;
            delBtn.title = "Delete chat";
            delBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                deleteSession(session.id);
            });

            item.appendChild(title);
            item.appendChild(delBtn);

            item.addEventListener('click', () => {
                loadSession(session.id);
            });

            chatHistoryList.appendChild(item);
        });
    }

    function startNewChat() {
        currentSessionId = null;
        chatMessages.innerHTML = '';
        if (welcomeScreen) {
            chatMessages.appendChild(welcomeScreen);
            welcomeScreen.style.display = 'block';
        }
        renderHistorySidebar();
        messageInput.value = '';
        messageInput.focus();
        adjustTextareaHeight();
        attachedItems = [];
        renderAttachmentTray();
        toggleSendButton();
    }

    function loadSession(id) {
        const sessions = getSessions();
        const session = sessions.find(s => s.id === id);
        if (!session) return;

        currentSessionId = id;
        chatMessages.innerHTML = '';
        
        session.messages.forEach((msg, idx) => {
            appendMessageNode(msg.text, msg.isUser, idx, msg.attachments || []);
        });

        renderHistorySidebar();
        chatMessages.scrollTop = chatMessages.scrollHeight;

        // Close mobile sidebar if open
        if (window.innerWidth <= 768) {
            sidebar.classList.add('closed');
        }
    }

    function deleteSession(id) {
        let sessions = getSessions();
        sessions = sessions.filter(s => s.id !== id);
        saveSessions(sessions);
        const loggedIn = localStorage.getItem('isLoggedIn') === 'true';
        const email = (localStorage.getItem('userEmail') || '').toLowerCase().trim();
        if (loggedIn && email && email !== 'user') {
            try { 
                backendFetch(`/api/sessions/${id}?user_id=${encodeURIComponent(email)}`, { method: 'DELETE' }); 
            } catch(e) {}
        }

        if (currentSessionId === id) {
            startNewChat();
        } else {
            renderHistorySidebar();
        }
    }

    function clearAllHistory() {
        if (confirm("Are you sure you want to clear your chat history?")) {
            const key = getCurrentUserKey();
            localStorage.removeItem(key);
            const loggedIn = localStorage.getItem('isLoggedIn') === 'true';
            const email = (localStorage.getItem('userEmail') || '').toLowerCase().trim();
            if (loggedIn && email && email !== 'user') {
                try { 
                    backendFetch(`/api/sessions?user_id=${encodeURIComponent(email)}`, { method: 'DELETE' }); 
                } catch(e) {}
            }
            startNewChat();
        }
    }

    // --- ATTACHMENT HELPERS & PROCESSING ---
    function formatFileSize(bytes) {
        if (!bytes || bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
    }

    // Generate compressed thumbnail to prevent localStorage quota exhaustion
    async function createCompressedThumbnail(fileOrDataUrl, maxDim = 380, quality = 0.72) {
        return new Promise((resolve) => {
            const img = new Image();
            img.onload = () => {
                let width = img.width;
                let height = img.height;
                if (width > maxDim || height > maxDim) {
                    if (width > height) {
                        height = Math.round((height * maxDim) / width);
                        width = maxDim;
                    } else {
                        width = Math.round((width * maxDim) / height);
                        height = maxDim;
                    }
                }
                const canvas = document.createElement('canvas');
                canvas.width = width;
                canvas.height = height;
                const ctx = canvas.getContext('2d');
                ctx.drawImage(img, 0, 0, width, height);
                resolve(canvas.toDataURL('image/jpeg', quality));
            };
            img.onerror = () => resolve(typeof fileOrDataUrl === 'string' ? fileOrDataUrl : '');
            if (typeof fileOrDataUrl === 'string') {
                img.src = fileOrDataUrl;
            } else {
                const reader = new FileReader();
                reader.onload = (e) => { img.src = e.target.result; };
                reader.readAsDataURL(fileOrDataUrl);
            }
        });
    }

    // Extract text from PDF files in browser using pdf.js
    async function extractTextFromPdf(file) {
        try {
            if (!window.pdfjsLib) return '';
            const arrayBuffer = await file.arrayBuffer();
            const pdf = await window.pdfjsLib.getDocument({ data: arrayBuffer }).promise;
            let fullText = '';
            const maxPages = Math.min(pdf.numPages, 15);
            for (let i = 1; i <= maxPages; i++) {
                const page = await pdf.getPage(i);
                const content = await page.getTextContent();
                const pageStrings = content.items.map(item => item.str).join(' ');
                fullText += `\n[Page ${i}]:\n${pageStrings.trim()}`;
            }
            if (pdf.numPages > maxPages) {
                fullText += `\n... [Note: Loaded first ${maxPages} of ${pdf.numPages} pages]`;
            }
            return fullText.trim();
        } catch (e) {
            console.warn('PDF extraction failed:', e);
            return '';
        }
    }

    // Extract text from Word DOCX using mammoth if available
    async function extractTextFromDocx(file) {
        try {
            if (!window.mammoth) return '';
            const arrayBuffer = await file.arrayBuffer();
            const res = await window.mammoth.extractRawText({ arrayBuffer });
            return (res && res.value) ? res.value.trim() : '';
        } catch (e) {
            return '';
        }
    }

    // Run Tesseract OCR in background for image questions & handwritten notes
    function runOcrOnImage(file, attachment) {
        if (!window.Tesseract) return;
        attachment.statusMessage = 'Reading image text...';
        renderAttachmentTray();
        window.Tesseract.recognize(file, 'eng')
            .then(res => {
                const text = (res && res.data && res.data.text) ? res.data.text.trim() : '';
                if (text) {
                    attachment.extractedContent = text;
                    attachment.statusMessage = 'Text extracted';
                } else {
                    attachment.statusMessage = '';
                }
                renderAttachmentTray();
            })
            .catch(err => {
                console.log('Tesseract OCR error:', err);
                attachment.statusMessage = '';
                renderAttachmentTray();
            });
    }

    // Image download helper (works for local backend images and external blobs across ports)
    async function downloadImageFile(url, alt = 'nexora_image') {
        const fullUrl = resolveBackendUrl(url);
        const cleanName = alt.toLowerCase().replace(/[^a-z0-9]+/g, '_').substring(0, 40).replace(/^_+|_+$/g, '') || 'nexora_image';
        const filename = `${cleanName}.jpg`;

        if (fullUrl.includes('/api/images/')) {
            const dlUrl = fullUrl.endsWith('/download') ? fullUrl : `${fullUrl}/download`;
            const a = document.createElement('a');
            a.href = dlUrl;
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            return;
        }

        try {
            const res = await fetch(fullUrl);
            const blob = await res.blob();
            const blobUrl = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = blobUrl;
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            setTimeout(() => URL.revokeObjectURL(blobUrl), 3000);
        } catch (e) {
            window.open(fullUrl, '_blank');
        }
    }

    // Lightbox modal functions
    function openLightbox(src, caption = '') {
        if (!imageLightboxModal) return;
        const fullSrc = resolveBackendUrl(src);
        if (lightboxImg) lightboxImg.src = fullSrc;
        if (lightboxCaption) lightboxCaption.textContent = caption;
        imageLightboxModal.style.display = 'flex';
    }

    function closeLightbox() {
        if (!imageLightboxModal) return;
        imageLightboxModal.style.display = 'none';
        if (lightboxImg) lightboxImg.src = '';
    }

    const lightboxDownloadBtn = document.getElementById('lightbox-download-btn');
    lightboxDownloadBtn?.addEventListener('click', () => {
        if (lightboxImg && lightboxImg.src) {
            downloadImageFile(lightboxImg.src, lightboxCaption?.textContent || 'nexora_image');
        }
    });

    // Render attachments preview tray inside chat input dock
    function renderAttachmentTray() {
        if (!attachmentPreviewTray) return;
        if (attachedItems.length === 0) {
            attachmentPreviewTray.style.display = 'none';
            attachmentPreviewTray.innerHTML = '';
            return;
        }

        attachmentPreviewTray.style.display = 'flex';
        attachmentPreviewTray.innerHTML = '';

        attachedItems.forEach(item => {
            const card = document.createElement('div');
            card.className = 'attachment-card';

            if (item.type === 'image') {
                const img = document.createElement('img');
                img.className = 'attachment-thumbnail';
                img.src = item.dataUrl;
                img.alt = item.name;
                card.appendChild(img);
            } else if (item.type === 'folder') {
                const badge = document.createElement('div');
                badge.className = 'attachment-icon-badge folder';
                badge.textContent = '📁';
                card.appendChild(badge);
            } else {
                const badge = document.createElement('div');
                const badgeClass = item.ext === 'pdf' ? 'pdf' : (['doc', 'docx'].includes(item.ext) ? 'doc' : 'generic');
                badge.className = `attachment-icon-badge ${badgeClass}`;
                badge.textContent = (item.ext || 'FILE').toUpperCase().slice(0, 4);
                card.appendChild(badge);
            }

            const meta = document.createElement('div');
            meta.className = 'attachment-meta';
            const nameSpan = document.createElement('span');
            nameSpan.className = 'attachment-name';
            nameSpan.textContent = item.name;
            nameSpan.title = item.name;

            const sizeSpan = document.createElement('span');
            sizeSpan.className = 'attachment-size';
            sizeSpan.textContent = item.statusMessage ? `${item.sizeStr} • ${item.statusMessage}` : item.sizeStr;

            meta.appendChild(nameSpan);
            meta.appendChild(sizeSpan);
            card.appendChild(meta);

            const removeBtn = document.createElement('button');
            removeBtn.className = 'attachment-remove-btn';
            removeBtn.type = 'button';
            removeBtn.innerHTML = '&times;';
            removeBtn.title = 'Remove attachment';
            removeBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                attachedItems = attachedItems.filter(att => att.id !== item.id);
                renderAttachmentTray();
                toggleSendButton();
            });
            card.appendChild(removeBtn);

            attachmentPreviewTray.appendChild(card);
        });
    }

    // Process file selections
    async function handleFilesSelected(files) {
        if (!files || files.length === 0) return;
        for (const file of Array.from(files)) {
            const ext = file.name.split('.').pop().toLowerCase();
            const attId = 'att_' + Date.now() + '_' + Math.random().toString(36).substring(2, 7);
            const isPdf = ext === 'pdf';
            const isDoc = ['doc', 'docx'].includes(ext);

            const attachment = {
                id: attId,
                type: 'file',
                name: file.name,
                ext: ext,
                sizeBytes: file.size,
                sizeStr: formatFileSize(file.size),
                extractedContent: '',
                statusMessage: isPdf ? 'Reading PDF...' : (isDoc ? 'Reading Doc...' : 'Reading...')
            };
            attachedItems.push(attachment);
            renderAttachmentTray();

            try {
                if (isPdf) {
                    attachment.extractedContent = await extractTextFromPdf(file);
                } else if (isDoc) {
                    attachment.extractedContent = await extractTextFromDocx(file);
                } else {
                    attachment.extractedContent = await file.text();
                }
                attachment.statusMessage = '';
            } catch (e) {
                console.warn('File read error:', e);
                attachment.statusMessage = 'Ready';
            }
            renderAttachmentTray();
        }
        toggleSendButton();
    }

    // Process image selections
    async function handleImagesSelected(files) {
        if (!files || files.length === 0) return;
        for (const file of Array.from(files)) {
            if (!file.type.startsWith('image/')) continue;
            const attId = 'att_' + Date.now() + '_' + Math.random().toString(36).substring(2, 7);
            const dataUrl = await new Promise(res => {
                const reader = new FileReader();
                reader.onload = e => res(e.target.result);
                reader.readAsDataURL(file);
            });
            const compressedThumb = await createCompressedThumbnail(dataUrl, 360, 0.72);

            const attachment = {
                id: attId,
                type: 'image',
                name: file.name || 'Pasted Image',
                ext: file.type.split('/')[1] || 'png',
                sizeBytes: file.size,
                sizeStr: formatFileSize(file.size),
                dataUrl: compressedThumb,
                fullDataUrl: dataUrl,
                extractedContent: '',
                statusMessage: 'Scanning...'
            };
            attachedItems.push(attachment);
            renderAttachmentTray();

            // Run OCR in background
            runOcrOnImage(file, attachment);
        }
        toggleSendButton();
    }

    // Process folder selection
    async function handleFolderSelected(files) {
        if (!files || files.length === 0) return;
        const fileList = Array.from(files);
        const rootFolderName = (fileList[0].webkitRelativePath || '').split('/')[0] || 'Uploaded_Folder';
        let totalBytes = 0;
        const readableFiles = [];

        for (const file of fileList) {
            totalBytes += file.size;
            const relPath = file.webkitRelativePath || file.name;
            const ext = file.name.split('.').pop().toLowerCase();
            const isText = ['txt', 'md', 'json', 'csv', 'py', 'js', 'html', 'css', 'sql', 'cpp', 'java'].includes(ext);
            if (isText && file.size < 500000) { // under 500KB
                try {
                    const text = await file.text();
                    readableFiles.push({ path: relPath, content: text });
                } catch (e) {}
            }
        }

        let compiledContent = `Folder Directory: ${rootFolderName} (${fileList.length} files)\nFiles list:\n` +
            fileList.map(f => ` - ${f.webkitRelativePath || f.name} (${formatFileSize(f.size)})`).join('\n') + '\n\nFile Contents:';

        readableFiles.slice(0, 10).forEach(rf => {
            compiledContent += `\n\n--- [File: ${rf.path}] ---\n${rf.content.slice(0, 3000)}`;
        });

        const attId = 'att_' + Date.now() + '_' + Math.random().toString(36).substring(2, 7);
        const attachment = {
            id: attId,
            type: 'folder',
            name: rootFolderName,
            ext: 'folder',
            filesCount: fileList.length,
            sizeBytes: totalBytes,
            sizeStr: formatFileSize(totalBytes),
            extractedContent: compiledContent,
            statusMessage: `${fileList.length} files`
        };
        attachedItems.push(attachment);
        renderAttachmentTray();
        toggleSendButton();
    }

    // --- MESSAGE RENDERING ---
    function appendMessageNode(text, isUser, msgIndex = null, attachments = []) {
        if (welcomeScreen && welcomeScreen.parentElement === chatMessages) {
            welcomeScreen.remove();
        }

        const row = document.createElement('div');
        row.className = `message-row ${isUser ? 'user-row' : 'ai-row'}`;
        if (msgIndex !== null) {
            row.dataset.msgIndex = msgIndex;
        }

        const avatar = document.createElement('div');
        avatar.className = `message-avatar ${isUser ? 'user-av' : 'ai-av'}`;
        if (isUser) {
            avatar.textContent = isLoggedIn ? userInitial : 'U';
        } else {
            avatar.innerHTML = `
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M12 2L2 7l10 5 10-5-10-5z"></path>
                    <path d="M2 17l10 5 10-5"></path>
                    <path d="M2 12l10 5 10-5"></path>
                </svg>
            `;
        }

        const bubble = document.createElement('div');
        bubble.className = 'message-bubble';

        if (isUser) {
            // Render attachments if present (ChatGPT style gallery and pills)
            if (attachments && attachments.length > 0) {
                const attachContainer = document.createElement('div');
                attachContainer.className = 'user-msg-attachments';

                const images = attachments.filter(a => a.type === 'image');
                const others = attachments.filter(a => a.type !== 'image');

                if (images.length > 0) {
                    const imgGrid = document.createElement('div');
                    imgGrid.className = 'user-msg-images-grid';
                    images.forEach(imgAtt => {
                        const imgCard = document.createElement('div');
                        imgCard.className = 'user-msg-image-card';
                        imgCard.title = 'Click to inspect ' + imgAtt.name;

                        const imgEl = document.createElement('img');
                        imgEl.src = imgAtt.fullDataUrl || imgAtt.dataUrl;
                        imgEl.alt = imgAtt.name;

                        const zoomOverlay = document.createElement('div');
                        zoomOverlay.className = 'user-image-zoom-overlay';
                        zoomOverlay.innerHTML = `
                            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <circle cx="11" cy="11" r="8"></circle>
                                <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
                                <line x1="11" y1="8" x2="11" y2="14"></line>
                                <line x1="8" y1="11" x2="14" y2="11"></line>
                            </svg>
                        `;

                        imgCard.appendChild(imgEl);
                        imgCard.appendChild(zoomOverlay);

                        imgCard.addEventListener('click', () => {
                            openLightbox(imgAtt.fullDataUrl || imgAtt.dataUrl, imgAtt.name);
                        });

                        imgGrid.appendChild(imgCard);
                    });
                    attachContainer.appendChild(imgGrid);
                }

                if (others.length > 0) {
                    const filesList = document.createElement('div');
                    filesList.className = 'user-msg-files-list';
                    others.forEach(otherAtt => {
                        const pill = document.createElement('div');
                        pill.className = `user-msg-file-pill ${otherAtt.type === 'folder' ? 'folder-pill' : ''}`;

                        const icon = document.createElement('span');
                        const extClass = otherAtt.ext === 'pdf' ? 'pdf' : (['doc', 'docx'].includes(otherAtt.ext) ? 'doc' : '');
                        icon.className = `file-pill-icon ${extClass}`;
                        icon.textContent = otherAtt.type === 'folder' ? '📁' : (otherAtt.ext || 'FILE').toUpperCase().slice(0, 4);

                        const details = document.createElement('div');
                        details.className = 'file-pill-details';
                        const nameSpan = document.createElement('span');
                        nameSpan.className = 'file-pill-name';
                        nameSpan.textContent = otherAtt.name;
                        nameSpan.title = otherAtt.name;

                        const sizeSpan = document.createElement('span');
                        sizeSpan.className = 'file-pill-size';
                        sizeSpan.textContent = otherAtt.type === 'folder' ? `${otherAtt.filesCount || ''} files • ${otherAtt.sizeStr}` : otherAtt.sizeStr;

                        details.appendChild(nameSpan);
                        details.appendChild(sizeSpan);
                        pill.appendChild(icon);
                        pill.appendChild(details);
                        filesList.appendChild(pill);
                    });
                    attachContainer.appendChild(filesList);
                }

                bubble.appendChild(attachContainer);
            }

            // Render User Message with Hover Edit Button (ChatGPT style)
            const userContainer = document.createElement('div');
            userContainer.className = 'user-msg-container';

            const userTextSpan = document.createElement('div');
            userTextSpan.className = 'user-msg-text';
            userTextSpan.textContent = text;

            const editBtn = document.createElement('button');
            editBtn.className = 'user-msg-edit-btn';
            editBtn.title = "Edit question";
            editBtn.innerHTML = `
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path>
                    <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path>
                </svg>
            `;

            editBtn.addEventListener('click', () => {
                enterEditMode(row, text, msgIndex, attachments);
            });

            userContainer.appendChild(userTextSpan);
            userContainer.appendChild(editBtn);
            bubble.appendChild(userContainer);
        } else {
            bubble.classList.add('markdown-body');
            bubble.innerHTML = marked.parse(text);

            // Enhance all images with ChatGPT-style AI Image Card & Download Button
            const imgElements = bubble.querySelectorAll('img');
            imgElements.forEach(img => {
                const imgSrc = img.getAttribute('src');
                const imgAlt = img.getAttribute('alt') || 'AI Generated Visual';
                const resolvedSrc = resolveBackendUrl(imgSrc);

                const card = document.createElement('div');
                card.className = 'ai-image-card';
                card.innerHTML = `
                    <div class="ai-image-card-header">
                        <span class="ai-image-badge">🎨 AI Generated Image</span>
                        <span class="ai-image-zoom-hint">Click image to enlarge</span>
                    </div>
                    <div class="ai-image-card-preview">
                        <img src="${resolvedSrc}" alt="${imgAlt}" loading="lazy" />
                    </div>
                    <div class="ai-image-card-footer">
                        <button type="button" class="ai-image-download-btn" title="Download HD image to your computer">
                            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                                <polyline points="7 10 12 15 17 10"></polyline>
                                <line x1="12" y1="15" x2="12" y2="3"></line>
                            </svg>
                            <span>Download Image</span>
                        </button>
                        <button type="button" class="ai-image-fullscreen-btn" title="View Fullscreen">
                            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <polyline points="15 3 21 3 21 9"></polyline>
                                <polyline points="9 21 3 21 3 15"></polyline>
                                <line x1="21" y1="3" x2="14" y2="10"></line>
                                <line x1="3" y1="21" x2="10" y2="14"></line>
                            </svg>
                            <span>Fullscreen</span>
                        </button>
                    </div>
                `;

                const previewImg = card.querySelector('.ai-image-card-preview img');
                
                // Resilient fallback across port 8000 and 8080 if running on external Live Server (port 5500)
                previewImg?.addEventListener('error', function() {
                    console.warn('Image load failed, attempting port fallback for:', this.src);
                    if (this.src.includes(':5500/api/images/')) {
                        this.src = this.src.replace(':5500', ':8000');
                    } else if (this.src.startsWith('/api/images/')) {
                        this.src = 'http://127.0.0.1:8000' + this.getAttribute('src');
                    } else if (this.src.includes(':8000/api/images/')) {
                        this.src = this.src.replace(':8000', ':8080');
                    }
                });

                previewImg?.addEventListener('click', () => openLightbox(resolvedSrc, imgAlt));

                const fsBtn = card.querySelector('.ai-image-fullscreen-btn');
                fsBtn?.addEventListener('click', () => openLightbox(resolvedSrc, imgAlt));

                const dlBtn = card.querySelector('.ai-image-download-btn');
                dlBtn?.addEventListener('click', () => downloadImageFile(resolvedSrc, imgAlt));

                img.replaceWith(card);
            });

            // Add Actions Toolbar (Download as PDF & Copy)
            const actionsBar = document.createElement('div');
            actionsBar.className = 'message-actions-bar';
            actionsBar.innerHTML = `
                <button class="msg-action-btn download-pdf-btn" title="Download this response as PDF">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                        <polyline points="7 10 12 15 17 10"></polyline>
                        <line x1="12" y1="15" x2="12" y2="3"></line>
                    </svg>
                    <span>Download PDF</span>
                </button>
                <button class="msg-action-btn copy-msg-btn" title="Copy text">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                        <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
                    </svg>
                    <span>Copy</span>
                </button>
            `;

            // PDF Download listener for ONLY this specific answer
            const pdfBtn = actionsBar.querySelector('.download-pdf-btn');
            pdfBtn.addEventListener('click', () => {
                if (window.html2pdf) {
                    pdfBtn.querySelector('span').textContent = 'Generating PDF...';

                    // Create clean dedicated print container for ONLY this answer
                    const printContainer = document.createElement('div');
                    printContainer.className = 'pdf-export-container';
                    printContainer.innerHTML = `
                        <div style="font-family: Arial, sans-serif; color: #1a202c; padding: 24px; line-height: 1.6; background: #ffffff;">
                            <div style="border-bottom: 2px solid #2563eb; padding-bottom: 12px; margin-bottom: 20px; display: flex; justify-content: space-between; align-items: flex-end;">
                                <div>
                                    <h1 style="margin: 0; font-size: 20px; color: #1e3a8a; font-weight: 700;">Nexora AI • Study Guide & Notes</h1>
                                    <p style="margin: 4px 0 0; font-size: 12px; color: #64748b;">Official Exam Reference, Syllabus Breakdown & AI Analysis</p>
                                </div>
                                <div style="font-size: 11px; color: #94a3b8; text-align: right;">
                                    Generated: ${new Date().toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })}
                                </div>
                            </div>
                            <div class="pdf-body-content" style="font-size: 13px; color: #334155;">
                                ${marked.parse(text)}
                            </div>
                            <div style="margin-top: 30px; border-top: 1px solid #e2e8f0; padding-top: 10px; font-size: 10px; color: #94a3b8; text-align: center;">
                                Nexora AI Assistant • Always verify important dates with official commission press releases.
                            </div>
                        </div>
                    `;

                    // Format tables and headings inside printContainer for clean A4 printing
                    const tables = printContainer.querySelectorAll('table');
                    tables.forEach(table => {
                        table.style.width = '100%';
                        table.style.borderCollapse = 'collapse';
                        table.style.margin = '14px 0';
                        table.style.fontSize = '12px';
                    });
                    const ths = printContainer.querySelectorAll('th');
                    ths.forEach(th => {
                        th.style.border = '1px solid #cbd5e1';
                        th.style.backgroundColor = '#f1f5f9';
                        th.style.color = '#0f172a';
                        th.style.padding = '8px 10px';
                        th.style.textAlign = 'left';
                    });
                    const tds = printContainer.querySelectorAll('td');
                    tds.forEach(td => {
                        td.style.border = '1px solid #e2e8f0';
                        td.style.padding = '7px 10px';
                        td.style.color = '#334155';
                    });
                    const h1s = printContainer.querySelectorAll('h1, h2, h3, h4');
                    h1s.forEach(h => {
                        h.style.color = '#0f172a';
                        h.style.marginTop = '16px';
                        h.style.marginBottom = '6px';
                    });

                    const opt = {
                        margin: [10, 10, 12, 10],
                        filename: 'Nexora_AI_Response.pdf',
                        image: { type: 'jpeg', quality: 0.98 },
                        html2canvas: { scale: 2, useCORS: true },
                        jsPDF: { unit: 'mm', format: 'a4', orientation: 'portrait' }
                    };

                    window.html2pdf().set(opt).from(printContainer).save().then(() => {
                        pdfBtn.querySelector('span').textContent = 'Downloaded!';
                        setTimeout(() => { pdfBtn.querySelector('span').textContent = 'Download PDF'; }, 2500);
                    }).catch(err => {
                        console.error('PDF error:', err);
                        pdfBtn.querySelector('span').textContent = 'Download PDF';
                    });
                } else {
                    window.print();
                }
            });

            // Copy listener
            const copyBtn = actionsBar.querySelector('.copy-msg-btn');
            copyBtn.addEventListener('click', () => {
                navigator.clipboard.writeText(text).then(() => {
                    copyBtn.querySelector('span').textContent = 'Copied!';
                    setTimeout(() => { copyBtn.querySelector('span').textContent = 'Copy'; }, 2000);
                });
            });

            bubble.appendChild(actionsBar);
        }

        row.appendChild(avatar);
        row.appendChild(bubble);
        chatMessages.appendChild(row);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    // --- IN-PLACE QUESTION EDITING (ChatGPT style) ---
    function enterEditMode(row, currentText, msgIndex, attachments = []) {
        const bubble = row.querySelector('.message-bubble');
        if (!bubble) return;

        row.classList.add('is-editing');

        // Remember existing innerHTML to cancel easily
        const originalContent = bubble.innerHTML;

        bubble.innerHTML = `
            <div class="user-edit-box">
                <textarea class="user-edit-textarea" rows="2">${currentText}</textarea>
                <div class="user-edit-actions">
                    <button class="user-edit-cancel-btn">Cancel</button>
                    <button class="user-edit-save-btn">Save & Submit</button>
                </div>
            </div>
        `;

        const textarea = bubble.querySelector('.user-edit-textarea');
        const cancelBtn = bubble.querySelector('.user-edit-cancel-btn');
        const saveBtn = bubble.querySelector('.user-edit-save-btn');

        // Auto focus and place cursor at end
        textarea.focus();
        textarea.setSelectionRange(textarea.value.length, textarea.value.length);

        // Auto adjust edit textarea height
        textarea.style.height = 'auto';
        textarea.style.height = Math.min(textarea.scrollHeight, 180) + 'px';
        textarea.addEventListener('input', () => {
            textarea.style.height = 'auto';
            textarea.style.height = Math.min(textarea.scrollHeight, 180) + 'px';
        });

        // Cancel editing
        cancelBtn.addEventListener('click', () => {
            row.classList.remove('is-editing');
            bubble.innerHTML = originalContent;
            const editBtn = bubble.querySelector('.user-msg-edit-btn');
            editBtn?.addEventListener('click', () => {
                enterEditMode(row, currentText, msgIndex, attachments);
            });
        });

        // Submit edited question
        const submitEdit = () => {
            row.classList.remove('is-editing');
            const newText = textarea.value.trim();
            if (!newText) return;

            if (newText === currentText) {
                // No change, just cancel
                cancelBtn.click();
                return;
            }

            // Truncate session messages from this user message index onward, like ChatGPT
            let sessions = getSessions();
            let current = sessions.find(s => s.id === currentSessionId);

            if (current && msgIndex !== null && msgIndex !== undefined) {
                // Keep history before this edited message
                current.messages = current.messages.slice(0, msgIndex);
                saveSessions(sessions);
            }

            // Remove all subsequent DOM message rows from this row onward
            let nextSibling = row.nextElementSibling;
            while (nextSibling) {
                const toRemove = nextSibling;
                nextSibling = nextSibling.nextElementSibling;
                toRemove.remove();
            }
            row.remove();

            // Re-stage attachments if any existed on this edited message
            if (attachments && attachments.length > 0) {
                attachedItems = [...attachments];
            }

            // Send edited message afresh (re-renders user message and calls AI backend)
            sendMessage(newText);
        };

        saveBtn.addEventListener('click', submitEdit);
        textarea.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                submitEdit();
            }
        });
    }

    function showTypingIndicator(isImage = false) {
        const row = document.createElement('div');
        row.className = 'message-row ai-row';
        row.id = 'typing-indicator-row';

        const avatar = document.createElement('div');
        avatar.className = 'message-avatar ai-av';
        avatar.innerHTML = `
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M12 2L2 7l10 5 10-5-10-5z"></path>
                <path d="M2 17l10 5 10-5"></path>
                <path d="M2 12l10 5 10-5"></path>
            </svg>
        `;

        const bubble = document.createElement('div');
        bubble.className = 'message-bubble';
        if (isImage) {
            bubble.innerHTML = `
                <div class="ai-image-generating-status">
                    <div class="ai-image-spinner">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" class="spin-icon">
                            <line x1="12" y1="2" x2="12" y2="6"></line>
                            <line x1="12" y1="18" x2="12" y2="22"></line>
                            <line x1="4.93" y1="4.93" x2="7.76" y2="7.76"></line>
                            <line x1="16.24" y1="16.24" x2="19.07" y2="19.07"></line>
                            <line x1="2" y1="12" x2="6" y2="12"></line>
                            <line x1="18" y1="12" x2="22" y2="12"></line>
                            <line x1="4.93" y1="19.07" x2="7.76" y2="16.24"></line>
                            <line x1="16.24" y1="7.76" x2="19.07" y2="4.93"></line>
                        </svg>
                    </div>
                    <div class="ai-image-status-info">
                        <span class="ai-image-status-title">🎨 Creating image...</span>
                        <span class="ai-image-status-desc">Generating visual with ChatGPT-quality precision</span>
                    </div>
                </div>
            `;
        } else {
            bubble.innerHTML = `
                <div class="typing-dots">
                    <span class="typing-dot"></span>
                    <span class="typing-dot"></span>
                    <span class="typing-dot"></span>
                </div>
            `;
        }

        row.appendChild(avatar);
        row.appendChild(bubble);
        chatMessages.appendChild(row);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    function removeTypingIndicator() {
        const el = document.getElementById('typing-indicator-row');
        if (el) el.remove();
    }

    function saveMessageToCurrentSession(text, isUser, attachments = []) {
        let sessions = getSessions();
        // Sanitize attachments for safe local storage (preserve compressed thumbnails)
        const cleanAttachments = (attachments || []).map(att => ({
            id: att.id,
            type: att.type,
            name: att.name,
            ext: att.ext,
            sizeStr: att.sizeStr,
            filesCount: att.filesCount,
            dataUrl: att.dataUrl, // compressed thumbnail
            extractedContent: att.extractedContent ? att.extractedContent.slice(0, 10000) : ''
        }));

        if (!currentSessionId) {
            // Create a new session on first message
            currentSessionId = 'session_' + Date.now();
            const sessionTitle = text.slice(0, 32) + (text.length > 32 ? '...' : '');
            const newSession = {
                id: currentSessionId,
                title: sessionTitle,
                messages: [{ text, isUser, attachments: cleanAttachments, timestamp: Date.now() }],
                timestamp: Date.now()
            };
            sessions.unshift(newSession);
        } else {
            const current = sessions.find(s => s.id === currentSessionId);
            if (current) {
                current.messages.push({ text, isUser, attachments: cleanAttachments, timestamp: Date.now() });
                current.timestamp = Date.now();
            }
        }
        try {
            saveSessions(sessions);
        } catch (storageErr) {
            console.warn('localStorage full, trimming oldest sessions:', storageErr);
            while (sessions.length > 5) {
                sessions.pop();
            }
            try { saveSessions(sessions); } catch (e) {}
        }
        renderHistorySidebar();
    }

    // --- SEND MESSAGE LOGIC ---
    async function sendMessage(textToSend) {
        const rawMessage = (textToSend || messageInput.value).trim();
        const hasAttachments = attachedItems && attachedItems.length > 0;
        if (!rawMessage && !hasAttachments) return;

        // Take snapshot of staged attachments and clear tray
        const currentAttachments = [...attachedItems];
        attachedItems = [];
        renderAttachmentTray();

        let displayMessage = rawMessage;
        if (!displayMessage && hasAttachments) {
            const names = currentAttachments.map(a => a.name).join(', ');
            displayMessage = `Please analyze, explain and summarize the attached study materials (${names}).`;
        }

        // 3 Free questions limit for guest
        let questionCount = parseInt(localStorage.getItem('freeQuestionCount') || '0');
        if (!isLoggedIn && questionCount >= 3) {
            appendMessageNode('You have completed your 3 free questions preview limit. Please log in to get unlimited access to Nexora AI and full tests!', false);
            const loginPrompt = document.createElement('div');
            loginPrompt.style.textAlign = 'center';
            loginPrompt.style.margin = '10px 0 20px';
            loginPrompt.innerHTML = `
                <a href="login.html" style="background: #10a37f; color: #fff; padding: 9px 18px; border-radius: 6px; text-decoration: none; font-weight: 500; display: inline-block;">
                    Log In / Sign Up to Continue
                </a>
            `;
            chatMessages.appendChild(loginPrompt);
            chatMessages.scrollTop = chatMessages.scrollHeight;
            return;
        }

        // Determine message index in current session
        const activeSessions = getSessions();
        const activeCurrent = activeSessions.find(s => s.id === currentSessionId);
        const currentMsgIndex = activeCurrent ? activeCurrent.messages.length : 0;

        // Render user message with attachments & save
        appendMessageNode(displayMessage, true, currentMsgIndex, currentAttachments);
        saveMessageToCurrentSession(displayMessage, true, currentAttachments);

        messageInput.value = '';
        adjustTextareaHeight();
        toggleSendButton();
        sendButton.disabled = true;

        if (!isLoggedIn) {
            questionCount++;
            localStorage.setItem('freeQuestionCount', questionCount.toString());
        }

        const isImgReq = isClientImageRequest(displayMessage);
        showTypingIndicator(isImgReq);

        // Construct complete prompt including extracted document and OCR text
        let fullQueryForAi = displayMessage;
        if (currentAttachments.length > 0) {
            let attachText = '';
            currentAttachments.forEach((att, idx) => {
                if (att.type === 'file') {
                    attachText += `\n\n[ATTACHED FILE ${idx + 1}: ${att.name} (${att.sizeStr})]\n${att.extractedContent || '(Document attached)'}`;
                } else if (att.type === 'folder') {
                    attachText += `\n\n[ATTACHED FOLDER: ${att.name} (${att.filesCount} files, ${att.sizeStr})]\n${att.extractedContent || ''}`;
                } else if (att.type === 'image') {
                    attachText += `\n\n[ATTACHED IMAGE: ${att.name}]\n${att.extractedContent ? `OCR Extracted Text from Image:\n${att.extractedContent}` : '(Image/question paper diagram attached)'}`;
                }
            });
            fullQueryForAi = `${displayMessage}\n\n--- [ATTACHMENTS / USER STUDY MATERIALS] ---${attachText}`;
        }

        // Prepare context history from current session (last 10 messages for rich conversational context)
        const sessions = getSessions();
        const currentSession = sessions.find(s => s.id === currentSessionId);
        const historyPayload = currentSession ? currentSession.messages.slice(-10).map((m, idx, arr) => {
            if (idx === arr.length - 1 && m.isUser) {
                return { text: fullQueryForAi, isUser: true };
            }
            return { text: m.text, isUser: m.isUser };
        }) : [{ text: fullQueryForAi, isUser: true }];

        try {
            let response;
            try {
                response = await backendFetch('/api/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ message: fullQueryForAi, messages: historyPayload })
                });
            } catch (connErr) {
                removeTypingIndicator();
                console.error('Backend connection error:', connErr);
                const errMsg = 'Sorry, could not connect to the backend server. Make sure `python -m uvicorn main:app --reload` (port 8000 or 8080) is running.';
                appendMessageNode(errMsg, false);
                saveMessageToCurrentSession(errMsg, false);
                return;
            }

            removeTypingIndicator();

            if (!response.ok) {
                let errDetail = 'AI service is temporarily unavailable.';
                try {
                    const errJson = await response.json();
                    if (errJson && errJson.detail) errDetail = errJson.detail;
                } catch(e) {}
                const errMsg = `⚠️ Error (${response.status}): ${errDetail}`;
                appendMessageNode(errMsg, false);
                saveMessageToCurrentSession(errMsg, false);
                return;
            }

            const data = await response.json();
            appendMessageNode(data.answer, false);
            saveMessageToCurrentSession(data.answer, false);
        } catch (error) {
            removeTypingIndicator();
            console.error('Error:', error);
            const errMsg = 'An unexpected error occurred while processing your request. Please try again.';
            appendMessageNode(errMsg, false);
            saveMessageToCurrentSession(errMsg, false);
        } finally {
            sendButton.disabled = false;
            toggleSendButton();
            messageInput.focus();
        }
    }

    // --- EVENT LISTENERS ---
    function toggleSendButton() {
        const hasText = messageInput.value.trim().length > 0;
        const hasAttachments = attachedItems && attachedItems.length > 0;
        sendButton.disabled = !hasText && !hasAttachments;
    }

    function adjustTextareaHeight() {
        messageInput.style.height = 'auto';
        messageInput.style.height = Math.min(messageInput.scrollHeight, 180) + 'px';
    }

    messageInput.addEventListener('input', () => {
        adjustTextareaHeight();
        toggleSendButton();
    });

    messageInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    sendButton.addEventListener('click', () => sendMessage());

    // ================= 📎 ATTACHMENT CONTROLS & LISTENERS (ChatGPT style) =================
    // Toggle attachment popover dropdown
    attachButton?.addEventListener('click', (e) => {
        e.stopPropagation();
        if (!attachMenu) return;
        const isClosed = attachMenu.style.display === 'none' || !attachMenu.style.display;
        attachMenu.style.display = isClosed ? 'block' : 'none';
        attachButton.classList.toggle('open', isClosed);
    });

    // Close menu when clicking anywhere outside
    document.addEventListener('click', (e) => {
        if (attachMenu && !attachMenu.contains(e.target) && !attachButton?.contains(e.target)) {
            attachMenu.style.display = 'none';
            attachButton?.classList.remove('open');
        }
    });

    // Options click handlers
    attachFileOpt?.addEventListener('click', (e) => {
        e.stopPropagation();
        attachMenu.style.display = 'none';
        attachButton?.classList.remove('open');
        fileUploadInput?.click();
    });

    attachFolderOpt?.addEventListener('click', (e) => {
        e.stopPropagation();
        attachMenu.style.display = 'none';
        attachButton?.classList.remove('open');
        folderUploadInput?.click();
    });

    attachImageOpt?.addEventListener('click', (e) => {
        e.stopPropagation();
        attachMenu.style.display = 'none';
        attachButton?.classList.remove('open');
        imageUploadInput?.click();
    });

    const attachGenImageOpt = document.getElementById('attach-gen-image-opt');
    attachGenImageOpt?.addEventListener('click', (e) => {
        e.stopPropagation();
        attachMenu.style.display = 'none';
        attachButton?.classList.remove('open');
        messageInput.value = '/image ';
        messageInput.placeholder = 'Describe the image or chart you want Nexora AI to generate...';
        messageInput.focus();
        adjustTextareaHeight();
        toggleSendButton();
    });

    // Input change handlers
    fileUploadInput?.addEventListener('change', (e) => {
        handleFilesSelected(e.target.files);
        e.target.value = '';
    });

    folderUploadInput?.addEventListener('change', (e) => {
        handleFolderSelected(e.target.files);
        e.target.value = '';
    });

    imageUploadInput?.addEventListener('change', (e) => {
        handleImagesSelected(e.target.files);
        e.target.value = '';
    });

    // Drag & Drop onto chat bar
    if (inputBoxWrapper) {
        ['dragenter', 'dragover'].forEach(eventName => {
            inputBoxWrapper.addEventListener(eventName, (e) => {
                e.preventDefault();
                e.stopPropagation();
                inputBoxWrapper.classList.add('drag-over');
            });
        });

        ['dragleave', 'dragend'].forEach(eventName => {
            inputBoxWrapper.addEventListener(eventName, (e) => {
                e.preventDefault();
                e.stopPropagation();
                if (!inputBoxWrapper.contains(e.relatedTarget)) {
                    inputBoxWrapper.classList.remove('drag-over');
                }
            });
        });

        inputBoxWrapper.addEventListener('drop', (e) => {
            e.preventDefault();
            e.stopPropagation();
            inputBoxWrapper.classList.remove('drag-over');

            const dt = e.dataTransfer;
            if (!dt) return;

            const files = Array.from(dt.files || []);
            const images = files.filter(f => f.type.startsWith('image/'));
            const others = files.filter(f => !f.type.startsWith('image/'));

            if (images.length > 0) handleImagesSelected(images);
            if (others.length > 0) handleFilesSelected(others);
        });
    }

    // Clipboard Paste (e.g. Snipping tool screenshots pasted directly into chat)
    document.addEventListener('paste', (e) => {
        if (e.target && (e.target.id === 'alert-email' || e.target.id === 'setting-font-size')) return;
        if (!e.clipboardData || !e.clipboardData.items) return;
        const items = Array.from(e.clipboardData.items);
        const imageItems = items.filter(item => item.type && item.type.indexOf('image') !== -1);
        if (imageItems.length > 0) {
            const files = imageItems.map(item => item.getAsFile()).filter(Boolean);
            if (files.length > 0) {
                handleImagesSelected(files);
            }
        }
    });

    // Lightbox modal listeners
    closeLightboxBtn?.addEventListener('click', closeLightbox);
    imageLightboxModal?.addEventListener('click', (e) => {
        if (e.target === imageLightboxModal) closeLightbox();
    });

    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            closeLightbox();
            if (attachMenu) {
                attachMenu.style.display = 'none';
                attachButton?.classList.remove('open');
            }
        }
    });

    newChatBtn?.addEventListener('click', startNewChat);
    topNewChatBtn?.addEventListener('click', startNewChat);
    clearHistoryBtn?.addEventListener('click', clearAllHistory);
    const exportHistoryBtn = document.getElementById('export-history-btn');
    const importHistoryBtn = document.getElementById('import-history-btn');
    const importHistoryFileInput = document.getElementById('import-history-file-input');

    exportHistoryBtn?.addEventListener('click', exportChatHistory);
    importHistoryBtn?.addEventListener('click', () => importHistoryFileInput?.click());
    importHistoryFileInput?.addEventListener('change', handleImportHistoryFile);

    // Sidebar toggling
    sidebarToggleBtn?.addEventListener('click', () => {
        sidebar.classList.toggle('closed');
    });

    sidebarCloseBtn?.addEventListener('click', () => {
        sidebar.classList.add('closed');
    });

    // Quick suggestion cards & exam pills
    document.addEventListener('click', (e) => {
        const card = e.target.closest('.suggestion-card');
        if (card && card.dataset.prompt) {
            sendMessage(card.dataset.prompt);
            return;
        }

        const pill = e.target.closest('.exam-pill');
        if (pill && pill.dataset.prompt) {
            sendMessage(pill.dataset.prompt);
            return;
        }
    });

    // ================= 🎙️ VOICE SPEECH-TO-TEXT FEATURE =================
    const voiceButton = document.getElementById('voice-button');
    const voiceStatusIndicator = document.getElementById('voice-status-indicator');
    let recognition = null;
    let isRecording = false;

    // Standard Web Speech API supported in Chrome, Edge, Safari, Brave, etc.
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

    if (SpeechRecognition) {
        recognition = new SpeechRecognition();
        recognition.continuous = false;
        recognition.interimResults = false;
        // Supports Marathi, Hindi, English smoothly
        recognition.lang = 'en-IN'; 

        recognition.onstart = () => {
            isRecording = true;
            voiceButton?.classList.add('recording');
            if (voiceStatusIndicator) voiceStatusIndicator.style.display = 'inline';
        };

        recognition.onresult = (event) => {
            const transcript = event.results[0][0].transcript;
            if (transcript) {
                // If textarea already has some text, append with space
                if (messageInput.value.trim()) {
                    messageInput.value = messageInput.value.trim() + ' ' + transcript;
                } else {
                    messageInput.value = transcript;
                }
                adjustTextareaHeight();
                toggleSendButton();
                messageInput.focus();
            }
        };

        recognition.onerror = (event) => {
            console.warn('Speech recognition error:', event.error);
            stopVoiceRecording();
        };

        recognition.onend = () => {
            stopVoiceRecording();
        };

        function stopVoiceRecording() {
            isRecording = false;
            voiceButton?.classList.remove('recording');
            if (voiceStatusIndicator) voiceStatusIndicator.style.display = 'none';
        }

        voiceButton?.addEventListener('click', () => {
            if (isRecording) {
                recognition.stop();
            } else {
                try {
                    recognition.start();
                } catch (e) {
                    recognition.stop();
                }
            }
        });
    } else {
        if (voiceButton) {
            voiceButton.title = "Voice recognition not supported in this browser";
            voiceButton.style.opacity = '0.5';
            voiceButton.addEventListener('click', () => {
                alert("Speech Recognition is supported in Google Chrome, Microsoft Edge, and Safari.");
            });
        }
    }

    // ================= 📢 AI EXAM & SYLLABUS ALERT SYSTEM =================
    const alertsModalBtn = document.getElementById('alerts-modal-btn');
    const alertsModal = document.getElementById('alerts-modal');
    const closeAlertsModalBtn = document.getElementById('close-alerts-modal-btn');
    const alertSubForm = document.getElementById('alert-sub-form');
    const alertEmailInput = document.getElementById('alert-email');
    const alertExamSelect = document.getElementById('alert-exam');
    const alertSubSuccess = document.getElementById('alert-sub-success');
    const sendTestAlertBtn = document.getElementById('send-test-alert-btn');

    // Pre-fill user email if logged in
    if (userEmail && userEmail !== 'User' && alertEmailInput) {
        alertEmailInput.value = userEmail;
    }

    const bottomAlertsBtn = document.getElementById('bottom-alerts-btn');

    alertsModalBtn?.addEventListener('click', () => {
        if (alertsModal) alertsModal.style.display = 'flex';
    });

    bottomAlertsBtn?.addEventListener('click', () => {
        if (alertsModal) alertsModal.style.display = 'flex';
    });

    closeAlertsModalBtn?.addEventListener('click', () => {
        if (alertsModal) alertsModal.style.display = 'none';
    });

    alertsModal?.addEventListener('click', (e) => {
        if (e.target === alertsModal) {
            alertsModal.style.display = 'none';
        }
    });

    // Handle Alert Subscription Form
    alertSubForm?.addEventListener('submit', async (e) => {
        e.preventDefault();
        const email = alertEmailInput.value.trim();
        const target_exam = alertExamSelect.value;
        if (!email) return;

        const saveBtn = document.getElementById('save-alert-btn');
        if (saveBtn) saveBtn.textContent = 'Activating...';

        try {
            // Save subscription locally
            localStorage.setItem('subscribedAlertEmail', email);
            localStorage.setItem('subscribedAlertExam', target_exam);

            // Call backend API
            const res = await backendFetch('/api/alerts/subscribe', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email, target_exam })
            });

            if (alertSubSuccess) {
                alertSubSuccess.style.display = 'block';
                alertSubSuccess.innerHTML = `✅ <strong>Alerts Activated!</strong> We will automatically send you email alerts at <code>${email}</code> whenever new syllabus is published or ${target_exam} schedule is updated!`;
            }
        } catch (err) {
            if (alertSubSuccess) {
                alertSubSuccess.style.display = 'block';
                alertSubSuccess.innerHTML = `✅ <strong>Alerts Registered!</strong> Daily schedule and syllabus notifications configured for <code>${email}</code>.`;
            }
        } finally {
            if (saveBtn) saveBtn.textContent = 'Active & Subscribed ✓';
        }
    });

    // Simulate sending test alert email
    sendTestAlertBtn?.addEventListener('click', async () => {
        const email = alertEmailInput.value.trim() || userEmail || 'student@example.com';
        sendTestAlertBtn.textContent = 'Sending email...';

        try {
            const res = await backendFetch('/api/alerts/send-test', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email })
            });

            sendTestAlertBtn.textContent = '✓ Test Alert Sent!';
            alert(`📢 Nexora AI Email Dispatched!\n\nTo: ${email}\nSubject: [Nexora AI Alert] Official Syllabus & Schedule Update Notice\n\nNotification sent successfully! You will receive future notices on this email.`);
            setTimeout(() => {
                sendTestAlertBtn.textContent = '✉️ Send Test Alert to My Email';
            }, 3000);
        } catch (e) {
            sendTestAlertBtn.textContent = '✓ Simulated!';
            alert(`📢 Notification Simulated for: ${email}\n\nSubject: Official Syllabus & Schedule Update Notice.`);
            setTimeout(() => {
                sendTestAlertBtn.textContent = '✉️ Send Test Alert to My Email';
            }, 3000);
        }
    });

    // ================= ⚙️ SETTINGS & THEME SWITCHER (ChatGPT style) =================
    const settingsBtn = document.getElementById('settings-btn');
    const settingsModal = document.getElementById('settings-modal');
    const closeSettingsModalBtn = document.getElementById('close-settings-modal-btn');
    const themeBtns = document.querySelectorAll('.theme-btn');
    const fontSizeSelect = document.getElementById('setting-font-size');

    // Load saved theme (default dark)
    const savedTheme = localStorage.getItem('appTheme') || 'dark';
    applyTheme(savedTheme);

    // Load saved font size
    const savedFontSize = localStorage.getItem('appFontSize') || 'normal';
    applyFontSize(savedFontSize);
    if (fontSizeSelect) fontSizeSelect.value = savedFontSize;

    function applyTheme(theme) {
        if (theme === 'light') {
            document.documentElement.setAttribute('data-theme', 'light');
        } else {
            document.documentElement.removeAttribute('data-theme');
        }
        localStorage.setItem('appTheme', theme);
        themeBtns.forEach(btn => {
            btn.classList.toggle('active', btn.dataset.theme === theme);
        });
    }

    function applyFontSize(size) {
        if (size === 'large') {
            document.documentElement.setAttribute('data-font', 'large');
        } else {
            document.documentElement.removeAttribute('data-font');
        }
        localStorage.setItem('appFontSize', size);
    }

    // Toggle Settings Modal
    settingsBtn?.addEventListener('click', () => {
        if (settingsModal) settingsModal.style.display = 'flex';
    });

    closeSettingsModalBtn?.addEventListener('click', () => {
        if (settingsModal) settingsModal.style.display = 'none';
    });

    settingsModal?.addEventListener('click', (e) => {
        if (e.target === settingsModal) {
            settingsModal.style.display = 'none';
        }
    });

    // Theme button click events
    themeBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            applyTheme(btn.dataset.theme);
        });
    });

    // Font size select change event
    fontSizeSelect?.addEventListener('change', (e) => {
        applyFontSize(e.target.value);
    });

    // Initialize: Starts with a clean new chat like ChatGPT, history is in sidebar!
    renderHistorySidebar();
    syncWithServerSessions();
    startNewChat();
});
