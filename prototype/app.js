/* MaDGA — Alpine app, block editor logic, sample data */

window.cmsApp = function () {
  return {
    /* ---------- theme + tweaks (URL param > localStorage > default) ---------- */
    theme: (new URLSearchParams(location.search).get('theme')) || localStorage.getItem('madga.theme') || 'dark',
    accent: (new URLSearchParams(location.search).get('accent')) || localStorage.getItem('madga.accent') || 'purple',
    editorStyle: (new URLSearchParams(location.search).get('editorStyle')) || localStorage.getItem('madga.editorStyle') || 'notion',
    tweaksOpen: false,

    /* ---------- broadcast drawer ---------- */
    broadcastOpen: false,
    broadcastChannel: 'tw',
    broadcastSchedule: 'with-post',
    broadcastEnabled: { tw: true, ms: true, bs: true, li: true, ig: false },
    broadcastDrafts: {
      tw: 'Why we rebuilt our publishing stack on Django — moving from Wagtail to something content teams actually enjoy. A note on what we learned, what we kept, and what we rewrote from scratch.\n\naitor.blog/blog/rebuilt-publishing-stack-django',
      ms: 'New post: Why we rebuilt our publishing stack on Django.\n\nA note on what we learned moving from Wagtail to MaDGA — what we kept, what we rewrote, and where the abstractions started to leak.\n\nhttps://aitor.blog/blog/rebuilt-publishing-stack-django\n\n#Django #Python #CMS #IndieWeb',
      bs: 'New post: Why we rebuilt our publishing stack on Django. What we learned moving off Wagtail, what we kept, and what we rewrote.\n\naitor.blog/blog/rebuilt-publishing-stack-django',
      li: 'After 14 months of running our content team on Wagtail, we rewrote our publishing stack on top of Django + HTMX.\n\nThree things drove the decision:\n\n— Editors were context-switching between admin and a live preview that never quite matched.\n— StreamFields were powerful, but the abstraction was leaking into editorial decisions.\n— The shape of our content (long essays + short notes + project pages) didn\'t map cleanly onto page trees.\n\nFull writeup, including the migration plan and the parts we still haven\'t finished:\n\nhttps://aitor.blog/blog/rebuilt-publishing-stack-django',
      ig: 'New on the blog: why we rewrote our publishing stack on Django, and what we learned about content tooling for non-technical teams along the way. Link in bio. ✍️',
    },
    channels: [
      { id: 'tw', platform: 'twitter',   name: 'Aitor Ruiz',     handle: '@aitorruiz',          limit: 280,  connected: true,  lastPost: '2 days ago' },
      { id: 'ms', platform: 'mastodon',  name: 'Aitor',          handle: '@aitor@hachyderm.io', limit: 500,  connected: true,  lastPost: '5 hours ago' },
      { id: 'bs', platform: 'bluesky',   name: 'Aitor Ruiz',     handle: '@aitor.bsky.social',  limit: 300,  connected: true,  lastPost: 'yesterday' },
      { id: 'li', platform: 'linkedin',  name: 'Aitor Ruiz',     handle: 'in/aitorruiz',        limit: 3000, connected: true,  lastPost: '1 week ago' },
      { id: 'ig', platform: 'instagram', name: 'aitor.writes',   handle: '@aitor.writes',       limit: 2200, connected: true,  lastPost: 'never' },
      { id: 'fb', platform: 'facebook',  name: '',               handle: '',                    limit: 63206,connected: false, lastPost: null },
      { id: 'th', platform: 'threads',   name: '',               handle: '',                    limit: 500,  connected: false, lastPost: null },
    ],
    get currentBroadcastChannel() {
      return this.channels.find(c => c.id === this.broadcastChannel) || this.channels[0];
    },
    get broadcastEnabledCount() {
      return Object.values(this.broadcastEnabled).filter(Boolean).length;
    },
    openBroadcast() { this.broadcastOpen = true; document.body.style.overflow = 'hidden'; },
    closeBroadcast() { this.broadcastOpen = false; document.body.style.overflow = ''; },

    setTheme(t) { this.theme = t; localStorage.setItem('madga.theme', t); },
    setAccent(a) { this.accent = a; localStorage.setItem('madga.accent', a); },
    setEditorStyle(s) { this.editorStyle = s; localStorage.setItem('madga.editorStyle', s); },

    /* ---------- routing ---------- */
    route: (new URLSearchParams(location.search).get('view')) || 'dashboard',
    editingPostId: null,
    sectionTab: 'all',
    selectedPostIds: [],

    go(route, opts = {}) {
      this.route = route;
      if (opts.postId !== undefined) this.editingPostId = opts.postId;
      const url = new URL(location.href);
      url.searchParams.set('view', route);
      history.replaceState(null, '', url);
      this.$nextTick(() => {
        const m = document.querySelector('.main-scroll');
        if (m) m.scrollTop = 0;
      });
    },

    newPost() {
      const id = 'new-' + Date.now();
      this.posts.unshift({
        id,
        title: '',
        slug: 'untitled',
        status: 'draft',
        author: 'Aitor R.',
        date: 'Just now',
        views: 0,
        category: 'Uncategorized',
        thumb: '',
      });
      this.editingPostId = id;
      this.go('editor', { postId: id });
    },

    editPost(id) {
      this.editingPostId = id;
      this.go('editor', { postId: id });
    },

    get currentPost() {
      return this.posts.find(p => p.id === this.editingPostId) || this.posts[0];
    },

    /* ---------- sample data ---------- */
    posts: [
      {
        id: 'p1',
        title: 'Why we rebuilt our publishing stack on Django',
        slug: 'rebuilt-publishing-stack-django',
        status: 'published', author: 'Aitor R.', date: 'May 6, 2026',
        views: 4218, category: 'Engineering', thumb: 'g1',
        excerpt: 'Notes from a year of replacing a tangle of WordPress plugins with one Django app we actually understand.',
      },
      {
        id: 'p2',
        title: 'Designing a CMS for people who do not love CMSes',
        slug: 'cms-for-people-who-dont-love-cmses',
        status: 'draft', author: 'Aitor R.', date: 'May 7, 2026',
        views: 0, category: 'Design', thumb: 'g2',
        excerpt: 'Most authors do not want a dashboard. They want a place to write. Here is how we held that line.',
      },
      {
        id: 'p3',
        title: 'Markdown vs blocks: stop having this argument',
        slug: 'markdown-vs-blocks',
        status: 'published', author: 'Mireia C.', date: 'May 4, 2026',
        views: 2891, category: 'Editorial', thumb: 'g3',
      },
      {
        id: 'p4',
        title: 'How we ship features in front of customers every Friday',
        slug: 'ship-friday',
        status: 'scheduled', author: 'Pau V.', date: 'May 10, 2026',
        views: 0, category: 'Engineering', thumb: 'g4',
      },
      {
        id: 'p5',
        title: 'The migration guide nobody wanted to write',
        slug: 'migration-guide',
        status: 'published', author: 'Aitor R.', date: 'May 1, 2026',
        views: 1542, category: 'Engineering', thumb: 'g5',
      },
      {
        id: 'p6',
        title: 'A short note on slow software',
        slug: 'slow-software',
        status: 'published', author: 'Mireia C.', date: 'Apr 28, 2026',
        views: 6430, category: 'Editorial', thumb: 'g6',
      },
      {
        id: 'p7',
        title: 'Server-rendered, client-enhanced',
        slug: 'server-rendered',
        status: 'draft', author: 'Pau V.', date: 'Apr 26, 2026',
        views: 0, category: 'Engineering', thumb: 'g7',
      },
      {
        id: 'p8',
        title: 'Django admin is not a product surface',
        slug: 'django-admin-not-a-product',
        status: 'published', author: 'Aitor R.', date: 'Apr 22, 2026',
        views: 3105, category: 'Engineering', thumb: 'g8',
      },
      {
        id: 'p9',
        title: 'Hiring our first technical writer',
        slug: 'hiring-tech-writer',
        status: 'archived', author: 'Mireia C.', date: 'Apr 14, 2026',
        views: 411, category: 'Team', thumb: 'g9',
      },
    ],

    pages: [
      { id: 'pg1', title: 'About', slug: '/about', status: 'published', updated: 'Apr 22, 2026', children: 0 },
      { id: 'pg2', title: 'Pricing', slug: '/pricing', status: 'published', updated: 'May 2, 2026', children: 0 },
      { id: 'pg3', title: 'Docs', slug: '/docs', status: 'published', updated: 'May 5, 2026', children: 14 },
      { id: 'pg4', title: 'Changelog', slug: '/changelog', status: 'published', updated: 'May 7, 2026', children: 0 },
      { id: 'pg5', title: 'Privacy policy', slug: '/legal/privacy', status: 'published', updated: 'Mar 8, 2026', children: 0 },
      { id: 'pg6', title: 'Careers', slug: '/careers', status: 'draft', updated: 'May 6, 2026', children: 3 },
    ],

    categories: [
      { id: 'c1', name: 'Engineering', slug: 'engineering', count: 42, color: '#6C63FF' },
      { id: 'c2', name: 'Design', slug: 'design', count: 18, color: '#44b78b' },
      { id: 'c3', name: 'Editorial', slug: 'editorial', count: 26, color: '#E89A3C' },
      { id: 'c4', name: 'Team', slug: 'team', count: 9, color: '#4F86FF' },
      { id: 'c5', name: 'Product', slug: 'product', count: 33, color: '#ff7a7a' },
    ],

    users: [
      { id: 'u1', name: 'Aitor Ruiz', email: 'aitor@madga.dev', role: 'Owner', last: 'Today', avatar: 'AR' },
      { id: 'u2', name: 'Mireia Costa', email: 'mireia@madga.dev', role: 'Editor', last: '2 hours ago', avatar: 'MC' },
      { id: 'u3', name: 'Pau Vila', email: 'pau@madga.dev', role: 'Author', last: 'Yesterday', avatar: 'PV' },
      { id: 'u4', name: 'Lucía Méndez', email: 'lucia@madga.dev', role: 'Author', last: '3 days ago', avatar: 'LM' },
      { id: 'u5', name: 'Theo Park', email: 'theo@madga.dev', role: 'Contributor', last: '1 week ago', avatar: 'TP' },
    ],

    /* ---------- posts list helpers ---------- */
    get filteredPosts() {
      if (this.sectionTab === 'all') return this.posts.filter(p => p.status !== 'archived');
      if (this.sectionTab === 'trash') return this.posts.filter(p => p.status === 'archived');
      return this.posts.filter(p => p.status === this.sectionTab);
    },
    get countAll() { return this.posts.filter(p => p.status !== 'archived').length; },
    get countPublished() { return this.posts.filter(p => p.status === 'published').length; },
    get countDraft() { return this.posts.filter(p => p.status === 'draft').length; },
    get countScheduled() { return this.posts.filter(p => p.status === 'scheduled').length; },
    get countTrash() { return this.posts.filter(p => p.status === 'archived').length; },

    toggleSelect(id) {
      const i = this.selectedPostIds.indexOf(id);
      if (i === -1) this.selectedPostIds.push(id);
      else this.selectedPostIds.splice(i, 1);
    },
    toggleSelectAll() {
      const ids = this.filteredPosts.map(p => p.id);
      const allSelected = ids.every(id => this.selectedPostIds.includes(id));
      this.selectedPostIds = allSelected ? [] : ids;
    },
    isAllSelected() {
      const ids = this.filteredPosts.map(p => p.id);
      return ids.length > 0 && ids.every(id => this.selectedPostIds.includes(id));
    },
    isSomeSelected() {
      const ids = this.filteredPosts.map(p => p.id);
      const sel = ids.filter(id => this.selectedPostIds.includes(id));
      return sel.length > 0 && sel.length < ids.length;
    },

    /* ---------- block editor ---------- */
    blocks: [
      { id: 'b1', type: 'paragraph', content: 'For about three years, our blog ran on a tower of WordPress plugins, a custom theme nobody dared touch, and one staging server that everyone agreed was haunted.' },
      { id: 'b2', type: 'h2', content: 'What we wanted instead' },
      { id: 'b3', type: 'paragraph', content: 'A CMS that felt like a writing tool, not a database explorer. Authors should never need to think about taxonomies, slugs, or which custom field controls the hero image.' },
      { id: 'b4', type: 'bullet', content: 'Block-based editing that works exactly the same on every page type' },
      { id: 'b5', type: 'bullet', content: 'No plugin marketplace — just a small, opinionated set of features we own' },
      { id: 'b6', type: 'bullet', content: 'Familiar enough that a WordPress author can publish on day one' },
      { id: 'b7', type: 'quote', content: 'A CMS is a product, not a configuration screen. The moment you ship one that needs a tutorial, you have already lost most of your authors.' },
      { id: 'b8', type: 'h2', content: 'Where we landed' },
      { id: 'b9', type: 'paragraph', content: 'MaDGA is a Django app that ships one editor, one set of content types, and a small admin surface. AlpineJS handles the live interactions; HTMX handles the partial updates. Boring in the best way.' },
      { id: 'b10', type: 'code', content: '# In your Django project\npip install madga\n\n# settings.py\nINSTALLED_APPS += ["madga"]\n\n# urls.py\npath("studio/", include("madga.urls"))' },
    ],

    slashOpen: false,
    slashFor: null,
    slashX: 0,
    slashY: 0,
    slashFilter: '',

    BLOCK_TYPES: [
      { id: 'paragraph', name: 'Text', desc: 'Just start writing with plain text', icon: 'paragraph', section: 'Basic' },
      { id: 'h1', name: 'Heading 1', desc: 'Big section heading', icon: 'h1', section: 'Basic' },
      { id: 'h2', name: 'Heading 2', desc: 'Medium section heading', icon: 'h2', section: 'Basic' },
      { id: 'h3', name: 'Heading 3', desc: 'Small section heading', icon: 'h3', section: 'Basic' },
      { id: 'bullet', name: 'Bullet list', desc: 'Create a simple bulleted list', icon: 'bullet', section: 'Lists' },
      { id: 'numbered', name: 'Numbered list', desc: 'Create a list with numbering', icon: 'numbered', section: 'Lists' },
      { id: 'quote', name: 'Quote', desc: 'Capture a quote', icon: 'quote', section: 'Content' },
      { id: 'callout', name: 'Callout', desc: 'Make writing stand out', icon: 'callout', section: 'Content' },
      { id: 'code', name: 'Code block', desc: 'Capture a code snippet', icon: 'code', section: 'Content' },
      { id: 'divider', name: 'Divider', desc: 'Visually divide blocks', icon: 'divider', section: 'Content' },
      { id: 'image', name: 'Image', desc: 'Upload or embed an image', icon: 'image', section: 'Media' },
    ],

    get blockTypeSections() {
      const filter = this.slashFilter.toLowerCase();
      const filtered = this.BLOCK_TYPES.filter(b =>
        !filter || b.name.toLowerCase().includes(filter) || b.id.includes(filter)
      );
      const sections = {};
      filtered.forEach(b => {
        sections[b.section] ??= [];
        sections[b.section].push(b);
      });
      return Object.entries(sections).map(([name, items]) => ({ name, items }));
    },

    addBlock(afterId, type = 'paragraph') {
      const idx = this.blocks.findIndex(b => b.id === afterId);
      const newBlock = { id: 'b' + Date.now(), type, content: '' };
      this.blocks.splice(idx + 1, 0, newBlock);
      this.$nextTick(() => {
        const el = document.querySelector(`[data-block-id="${newBlock.id}"] .block-content`);
        if (el) el.focus();
      });
    },

    changeBlockType(id, type) {
      const b = this.blocks.find(x => x.id === id);
      if (b) b.type = type;
      this.slashOpen = false;
    },

    deleteBlock(id) {
      const idx = this.blocks.findIndex(b => b.id === id);
      if (idx === -1) return;
      this.blocks.splice(idx, 1);
      if (this.blocks.length === 0) {
        this.blocks.push({ id: 'b' + Date.now(), type: 'paragraph', content: '' });
      }
    },

    moveBlock(id, dir) {
      const idx = this.blocks.findIndex(b => b.id === id);
      const target = idx + dir;
      if (target < 0 || target >= this.blocks.length) return;
      const [b] = this.blocks.splice(idx, 1);
      this.blocks.splice(target, 0, b);
    },

    duplicateBlock(id) {
      const idx = this.blocks.findIndex(b => b.id === id);
      if (idx === -1) return;
      const original = this.blocks[idx];
      this.blocks.splice(idx + 1, 0, { ...original, id: 'b' + Date.now() });
    },

    openSlash(blockId, ev) {
      const target = ev?.currentTarget?.closest('.block')?.querySelector('.block-content');
      const r = (target || ev?.currentTarget).getBoundingClientRect();
      this.slashOpen = true;
      this.slashFor = blockId;
      this.slashFilter = '';
      this.slashX = r.left;
      this.slashY = r.bottom + 6;
    },

    handleEditorKeydown(blockId, ev) {
      if (ev.key === '/' && !this.slashOpen) {
        this.openSlash(blockId, ev);
      } else if (ev.key === 'Escape') {
        this.slashOpen = false;
      } else if (ev.key === 'Enter' && !ev.shiftKey) {
        const block = this.blocks.find(b => b.id === blockId);
        if (block && block.type !== 'code') {
          ev.preventDefault();
          this.addBlock(blockId, 'paragraph');
        }
      } else if (ev.key === 'Backspace') {
        const block = this.blocks.find(b => b.id === blockId);
        const el = ev.currentTarget;
        if (block && el.textContent === '' && this.blocks.length > 1) {
          ev.preventDefault();
          const idx = this.blocks.findIndex(b => b.id === blockId);
          this.deleteBlock(blockId);
          this.$nextTick(() => {
            const prev = this.blocks[Math.max(0, idx - 1)];
            const prevEl = document.querySelector(`[data-block-id="${prev.id}"] .block-content`);
            if (prevEl) {
              prevEl.focus();
              const range = document.createRange();
              range.selectNodeContents(prevEl);
              range.collapse(false);
              const sel = window.getSelection();
              sel.removeAllRanges();
              sel.addRange(range);
            }
          });
        }
      }
    },

    /* ---------- editor right rail state ---------- */
    railSections: { status: true, seo: true, featured: true, organization: true },
    toggleRailSection(s) { this.railSections[s] = !this.railSections[s]; },

    postStatus: 'draft',
    publishDate: '2026-05-08T09:00',
    metaTitle: '',
    metaDescription: '',
    focusKeyword: '',
    featuredImage: '',
    selectedCategory: 'Engineering',
    tags: ['django', 'cms', 'publishing'],
    excerpt: '',

    /* ---------- settings ---------- */
    settingsTab: 'general',

    /* ---------- channels ---------- */
    channels: [
      { id: 'tw', platform: 'twitter',   name: 'X (Twitter)', handle: '@aitorruiz',          connected: true,  paused: false, lastPosted: '2 days ago',  reach: '4.2k followers',    limit: 280  },
      { id: 'ms', platform: 'mastodon',  name: 'Mastodon',    handle: '@aitor@hachyderm.io', connected: true,  paused: false, lastPosted: '5 hours ago', reach: '1.8k followers',    limit: 500  },
      { id: 'bs', platform: 'bluesky',   name: 'Bluesky',     handle: '@aitor.bsky.social',  connected: true,  paused: false, lastPosted: '2 days ago',  reach: '920 followers',     limit: 300  },
      { id: 'li', platform: 'linkedin',  name: 'LinkedIn',    handle: 'in/aitorruiz',        connected: true,  paused: true,  lastPosted: '3 weeks ago', reach: '3.4k connections', limit: 3000 },
      { id: 'ig', platform: 'instagram', name: 'Instagram',   handle: '—',                   connected: false, paused: false, lastPosted: '—',           reach: '—',                limit: 2200 },
      { id: 'th', platform: 'threads',   name: 'Threads',     handle: '—',                   connected: false, paused: false, lastPosted: '—',           reach: '—',                limit: 500  },
    ],
    broadcastDrafts: {
      tw: 'New essay: Why we rebuilt our publishing stack on Django.\n\nNotes from a year of replacing a tangle of WordPress plugins with one Django app we actually understand.\n\naitor.blog/blog/rebuilt-publishing-stack-django',
      ms: 'New on the blog — Why we rebuilt our publishing stack on Django.\n\nA year of replacing WordPress plugins with one Django app we actually understand. Trade-offs, surprises, and what we’d do differently.\n\n#Django #Writing #Python\n\nhttps://aitor.blog/blog/rebuilt-publishing-stack-django',
      bs: 'New essay: Why we rebuilt our publishing stack on Django.\n\nA year of replacing WordPress plugins with one Django app we actually understand.\n\naitor.blog/blog/rebuilt-publishing-stack-django',
      li: 'After a year of running our publishing stack on Django, here is what we learned — and why we replaced a tangle of WordPress plugins with one app we actually understand.\n\nFull essay: aitor.blog/blog/rebuilt-publishing-stack-django',
      ig: 'New essay on the blog. Link in bio.\n\nWhy we rebuilt our publishing stack on Django — a year of trade-offs and surprises.',
    },
    broadcastEnabled: { tw: true, ms: true, bs: true, li: false, ig: false },
    broadcastOpen: false,
    broadcastChannel: 'tw',
    broadcastSchedule: 'now',
    openBroadcast(initialChannel) {
      this.broadcastChannel = initialChannel || 'tw';
      this.broadcastOpen = true;
    },
    closeBroadcast() { this.broadcastOpen = false; },
    get currentBroadcastChannel() {
      return this.channels.find(c => c.id === this.broadcastChannel) || this.channels[0];
    },
    get broadcastEnabledCount() {
      return Object.values(this.broadcastEnabled).filter(Boolean).length;
    },
    recentBroadcasts: [
      { id: 'b1', post: 'Why we rebuilt our publishing stack on Django', date: 'May 6, 2026', channels: ['tw','ms','bs'],      reach: '12.3k', status: 'published' },
      { id: 'b2', post: 'Three weeks with the new editor',               date: 'Apr 22, 2026', channels: ['tw','ms','bs','li'], reach: '8.1k',  status: 'published' },
      { id: 'b3', post: 'Notes on shipping fast (and slow)',             date: 'Apr 9, 2026',  channels: ['tw','ms','bs'],      reach: '6.4k',  status: 'published' },
      { id: 'b4', post: 'A field guide to Django signals',               date: 'May 8, 2026',  channels: ['tw','ms','bs'],      reach: '—',     status: 'scheduled' },
    ],

    /* ---------- site / theme builder ---------- */
    siteTokens: {
      accentName: 'Indigo',
      accentHex: '#6C63FF',
      headingFont: 'Geist',
      bodyFont: 'Geist',
      scale: 1.0,
      radius: 8,
      density: 'comfortable',
      mode: 'auto',
    },
    accentSwatches: [
      { name: 'Indigo', hex: '#6C63FF' },
      { name: 'Django', hex: '#44b78b' },
      { name: 'Cobalt', hex: '#4F86FF' },
      { name: 'Amber', hex: '#E89A3C' },
      { name: 'Rose',   hex: '#ff7a89' },
      { name: 'Plum',   hex: '#8a5ec9' },
    ],

    layoutTab: 'homepage',
    layouts: {
      homepage: { selected: 'editorial', options: [
        { id: 'editorial', name: 'Editorial', desc: 'Hero, featured posts grid, newsletter band.', diagram: 'hero-grid' },
        { id: 'magazine',  name: 'Magazine',  desc: 'Lead story plus categorized strips. For frequent publishers.', diagram: 'hero-cols' },
        { id: 'minimal',   name: 'Minimal',   desc: 'Just a chronological list of titles. No hero, no images.', diagram: 'list' },
      ]},
      blogIndex: { selected: 'list', options: [
        { id: 'list',    name: 'Editorial list', desc: 'Date · Title · Excerpt rows, sorted newest first.', diagram: 'list' },
        { id: 'grid',    name: 'Card grid',      desc: '3 columns of cards with featured images.', diagram: 'hero-grid' },
        { id: 'compact', name: 'Compact',        desc: 'Just titles and dates, like a TOC.', diagram: 'list-tight' },
      ]},
      postDetail: { selected: 'classic', options: [
        { id: 'classic',    name: 'Classic',    desc: 'Title, lede, featured image, body — standard editorial.', diagram: 'article' },
        { id: 'longform',   name: 'Longform',   desc: 'No featured image, drop cap, wider body.', diagram: 'article-tight' },
        { id: 'asymmetric', name: 'Asymmetric', desc: 'Title left, body right, sticky meta column.', diagram: 'sidebar' },
      ]},
      staticPage: { selected: 'simple', options: [
        { id: 'simple',  name: 'Simple',       desc: 'Title and body, centered. For about, contact, legal.', diagram: 'article' },
        { id: 'sidebar', name: 'With sidebar', desc: 'Body plus secondary nav on the right.', diagram: 'sidebar' },
        { id: 'docs',    name: 'Docs',         desc: 'TOC left, body center, on-page anchors.', diagram: 'docs' },
      ]},
    },

    siteNav: [
      { id: 'n1', label: 'Home',       href: '/',           locked: true },
      { id: 'n2', label: 'Writing',    href: '/blog',       locked: false },
      { id: 'n3', label: 'About',      href: '/about',      locked: false },
      { id: 'n4', label: 'Talks',      href: '/talks',      locked: false },
      { id: 'n5', label: 'Newsletter', href: '/newsletter', locked: false },
    ],
    footerColumns: [
      { id: 'fc1', title: 'Writing',   links: ['All essays', 'Engineering', 'Editorial', 'Product'] },
      { id: 'fc2', title: 'Elsewhere', links: ['GitHub', 'Mastodon', 'RSS', 'Email'] },
      { id: 'fc3', title: 'Site',      links: ['About', 'Now', 'Colophon', 'Uses'] },
    ],

    homepageBlocks: [
      { id: 'hb1', type: 'hero',       title: 'Hero',             desc: 'Big tagline, intro, hero image.',         enabled: true,  meta: 'Tagline + image' },
      { id: 'hb2', type: 'featured',   title: 'Recent writing',   desc: 'Latest 3 posts as cards.',                enabled: true,  meta: '3 cards · auto' },
      { id: 'hb3', type: 'projects',   title: 'Projects strip',   desc: 'Side projects with links.',               enabled: false, meta: '0 items' },
      { id: 'hb4', type: 'newsletter', title: 'Newsletter band',  desc: 'Email capture with one-line pitch.',      enabled: true,  meta: 'aitor.blog/dispatch' },
      { id: 'hb5', type: 'about',      title: 'About preview',    desc: 'Short bio with a link to /about.',        enabled: false, meta: '~80 words' },
      { id: 'hb6', type: 'footer',     title: 'Footer',           desc: '4 columns of links plus copyright.',      enabled: true,  meta: '4 columns', locked: true },
    ],

    themes: [
      { id: 'essay',      name: 'Essay',     author: 'MaDGA',    desc: 'Clean, opinionated theme for personal writing. Editorial type, generous whitespace, full-bleed featured images.', installed: true,  active: true,  accent: '#6C63FF', tag: 'Official' },
      { id: 'magazine',   name: 'Magazine',  author: 'MaDGA',    desc: 'Multi-column lead story homepage with categorized post strips. Built for sites publishing daily.',                installed: true,  active: false, accent: '#E89A3C', tag: 'Official' },
      { id: 'portfolio',  name: 'Portfolio', author: 'MaDGA',    desc: 'Project-first homepage with case studies and a sidebar TOC. Writing lives in /notes.',                              installed: false, active: false, accent: '#44b78b', tag: 'Official' },
      { id: 'docs',       name: 'Docs',      author: 'MaDGA',    desc: 'Sidebar navigation, anchor scrolling, code blocks. For product documentation.',                                    installed: false, active: false, accent: '#4F86FF', tag: 'Official' },
      { id: 'dispatch',   name: 'Dispatch',  author: 'Anaïs Q.', desc: 'Newsletter-first theme. Big email capture, archive-as-homepage, paid subscriber gating.',                          installed: false, active: false, accent: '#ff7a89', tag: 'Community' },
      { id: 'bare',       name: 'Bare',      author: 'Theo P.',  desc: 'No images, no nav, just writing. Inspired by 90s personal pages.',                                                  installed: false, active: false, accent: '#1a1a1a', tag: 'Community' },
    ],
    themeFilter: 'all',
    get filteredThemes() {
      if (this.themeFilter === 'installed') return this.themes.filter(t => t.installed);
      if (this.themeFilter === 'official')  return this.themes.filter(t => t.tag === 'Official');
      if (this.themeFilter === 'community') return this.themes.filter(t => t.tag === 'Community');
      return this.themes;
    },

    moveSiteNav(id, dir) {
      const i = this.siteNav.findIndex(n => n.id === id);
      const t = i + dir;
      if (t < 0 || t >= this.siteNav.length) return;
      const [n] = this.siteNav.splice(i, 1);
      this.siteNav.splice(t, 0, n);
    },
    moveHomeBlock(id, dir) {
      const i = this.homepageBlocks.findIndex(b => b.id === id);
      const t = i + dir;
      if (t < 0 || t >= this.homepageBlocks.length) return;
      const [b] = this.homepageBlocks.splice(i, 1);
      this.homepageBlocks.splice(t, 0, b);
    },

    /* ---------- preview ---------- */
    previewView: 'post', // 'landing' | 'blog' | 'post' | 'page' | 'about'
    previewPageId: 'pg1',
    previewDevice: 'desktop', // 'desktop' | 'tablet' | 'mobile'
    previewReturnRoute: 'editor',

    openPreview(view = 'post', opts = {}) {
      this.previewView = view;
      if (opts.pageId) this.previewPageId = opts.pageId;
      if (opts.postId) this.editingPostId = opts.postId;
      this.previewReturnRoute = this.route === 'preview' ? this.previewReturnRoute : (this.route || 'dashboard');
      this.go('preview');
    },

    closePreview() {
      this.go(this.previewReturnRoute || 'dashboard');
    },

    get previewPage() {
      return this.pages.find(p => p.id === this.previewPageId) || this.pages[0];
    },

    previewUrl() {
      const base = 'aitor.blog';
      if (this.previewView === 'landing') return base + '/';
      if (this.previewView === 'blog') return base + '/blog';
      if (this.previewView === 'post') {
        const p = this.currentPost;
        return base + '/blog/' + (p?.slug || 'untitled');
      }
      if (this.previewView === 'page' || this.previewView === 'about') {
        const slug = this.previewView === 'about' ? '/about' : (this.previewPage?.slug || '/about');
        return base + slug;
      }
      return base;
    },

    /* posts in publication order for landing/blog */
    get publishedPosts() {
      return this.posts.filter(p => p.status === 'published');
    },

    /* ---------- init ---------- */
    init() {
      // numbered list ordering attribute (for ::before)
      this.$watch('blocks', () => this.renumberLists());
      this.renumberLists();
      // global slash close on click
      document.addEventListener('click', (e) => {
        if (!e.target.closest('.slash-menu') && !e.target.closest('.block-handle.add')) {
          this.slashOpen = false;
        }
      });
    },

    renumberLists() {
      let n = 0;
      this.$nextTick(() => {
        document.querySelectorAll('.block').forEach(el => {
          if (el.classList.contains('numbered')) {
            n += 1;
            el.querySelector('.block-content')?.setAttribute('data-num', n);
          } else {
            n = 0;
          }
        });
      });
    },

    /* ---------- helpers ---------- */
    formatNumber(n) {
      if (n >= 1000) return (n / 1000).toFixed(n >= 10000 ? 0 : 1) + 'k';
      return String(n);
    },

    greetingText() {
      const h = new Date().getHours();
      if (h < 12) return 'Good morning, Aitor';
      if (h < 18) return 'Good afternoon, Aitor';
      return 'Good evening, Aitor';
    },

    today() {
      return new Date().toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric' });
    },
  };
};
