// Small enhancements for the FragranSoul storefront.
// Every page works without this file; it only makes things smoother.

const root = document.documentElement;
root.classList.add("js");

const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
const hasMouse = window.matchMedia("(hover: hover) and (pointer: fine)").matches;

// ---- Sound ----
// Small interface sounds, made in the browser (there are no audio files).
// Browsers only allow sound after the visitor has clicked or pressed a key,
// so nothing plays before that. The header button mutes it, and the choice
// is remembered on this device.
const sound = (function () {
    const AudioContext = window.AudioContext || window.webkitAudioContext;
    const toggle = document.querySelector("[data-sound-toggle]");
    let enabled = Boolean(AudioContext);
    let context = null;

    try {
        if (localStorage.getItem("sound") === "off") {
            enabled = false;
        }
    } catch (error) {
        // Storage blocked: sound simply starts on each visit.
    }

    function showState() {
        if (toggle) {
            toggle.setAttribute("aria-pressed", enabled);
            toggle.hidden = !AudioContext;
        }
    }

    // Created on the first click or key press, as browsers require.
    function unlock() {
        if (!context && enabled) {
            context = new AudioContext();
        }
        if (context && context.state === "suspended") {
            context.resume();
        }
        startMusic();
    }

    // -- Background music --
    // If a music file has been added to the site it plays from its starting
    // point, quietly, and carries on from where it was on the next page.
    // Otherwise the built-in loop below plays instead.
    const track = document.querySelector("[data-music]");
    const musicVolume = 0.16;
    let musicOn = false;
    let pad = null;
    let fade = null;

    function fadeTrack(to, done) {
        clearInterval(fade);
        fade = setInterval(() => {
            if (Math.abs(to - track.volume) <= 0.01) {
                track.volume = to;
                clearInterval(fade);
                if (done) {
                    done();
                }
            } else {
                track.volume += Math.sign(to - track.volume) * 0.01;
            }
        }, 60);
    }

    function startTrack() {
        const start = Number(track.dataset.start) || 0;
        let resumeAt = start;
        try {
            resumeAt = Number(sessionStorage.getItem("musicAt")) || start;
        } catch (error) {
            // Storage blocked: the track starts from its starting point.
        }

        track.volume = 0;
        const begin = () => {
            // Past the end (or too close to it): go back to the starting point.
            if (track.duration && resumeAt > track.duration - 2) {
                resumeAt = start;
            }
            track.currentTime = resumeAt;
            track.play().then(() => fadeTrack(musicVolume)).catch(() => {
                musicOn = false;
            });
        };
        if (track.readyState >= 1) {
            begin();
        } else {
            track.addEventListener("loadedmetadata", begin, { once: true });
            track.load();
        }
    }

    if (track) {
        // When the track finishes it begins again from its starting point.
        track.addEventListener("ended", () => {
            track.currentTime = Number(track.dataset.start) || 0;
            track.play().catch(() => {});
        });
        window.addEventListener("pagehide", () => {
            try {
                sessionStorage.setItem("musicAt", String(track.currentTime));
            } catch (error) {
                // The next page just starts the track over.
            }
        });
    }

    // The built-in music: an original, laid-back four-bar loop. Electric-piano
    // chords, a soft bass, a sparse melody and a gentle beat, all made from
    // oscillators and filtered noise and scheduled a little ahead of time.
    function startLoop() {
        const beat = 60 / 74;
        const hz = (note) => 440 * Math.pow(2, (note - 69) / 12);

        // One bar each: bass note, chord notes, and melody as [beat, note, beats].
        const bars = [
            { bass: 38, chord: [54, 57, 61, 64], tune: [[0.5, 73, 1], [2, 69, 1.5]] },
            { bass: 35, chord: [57, 59, 62, 66], tune: [[1, 71, 0.75], [2.5, 66, 1.5]] },
            { bass: 40, chord: [55, 59, 62, 66], tune: [[0.5, 74, 1], [2, 71, 1], [3.25, 69, 0.75]] },
            { bass: 33, chord: [55, 59, 61, 66], tune: [[1.5, 73, 0.5], [2, 76, 1.5]] },
        ];

        const master = context.createGain();
        const warmth = context.createBiquadFilter();
        warmth.type = "lowpass";
        warmth.frequency.value = 2600;
        master.gain.setValueAtTime(0.0001, context.currentTime);
        master.gain.exponentialRampToValueAtTime(0.6, context.currentTime + 3);
        warmth.connect(master).connect(context.destination);

        // One second of noise, reused for the hi-hat and the rim click.
        const noise = context.createBuffer(1, context.sampleRate, context.sampleRate);
        const samples = noise.getChannelData(0);
        for (let index = 0; index < samples.length; index += 1) {
            samples[index] = Math.random() * 2 - 1;
        }

        // A note with a soft attack that eases off and is released at its end.
        function note(frequency, when, length, volume, shape, detune) {
            const oscillator = context.createOscillator();
            const gain = context.createGain();
            oscillator.type = shape;
            oscillator.frequency.value = frequency;
            oscillator.detune.value = detune || 0;
            gain.gain.setValueAtTime(0.0001, when);
            gain.gain.exponentialRampToValueAtTime(volume, when + 0.03);
            gain.gain.exponentialRampToValueAtTime(volume * 0.45, when + length * 0.6);
            gain.gain.exponentialRampToValueAtTime(0.0001, when + length);
            oscillator.connect(gain).connect(warmth);
            oscillator.start(when);
            oscillator.stop(when + length + 0.05);
        }

        function keys(notes, when, length, volume) {
            notes.forEach((value) => {
                note(hz(value), when, length, volume, "sine");
                note(hz(value), when, length, volume * 0.6, "triangle", 6);
            });
        }

        function kick(when) {
            const oscillator = context.createOscillator();
            const gain = context.createGain();
            oscillator.frequency.setValueAtTime(120, when);
            oscillator.frequency.exponentialRampToValueAtTime(45, when + 0.12);
            gain.gain.setValueAtTime(0.22, when);
            gain.gain.exponentialRampToValueAtTime(0.0001, when + 0.26);
            oscillator.connect(gain).connect(warmth);
            oscillator.start(when);
            oscillator.stop(when + 0.3);
        }

        function hiss(when, length, volume, type, frequency) {
            const source = context.createBufferSource();
            const filter = context.createBiquadFilter();
            const gain = context.createGain();
            source.buffer = noise;
            filter.type = type;
            filter.frequency.value = frequency;
            gain.gain.setValueAtTime(volume, when);
            gain.gain.exponentialRampToValueAtTime(0.0001, when + length);
            source.connect(filter).connect(gain).connect(warmth);
            source.start(when, Math.random() * 0.5, length + 0.02);
        }

        function scheduleBar(index, start) {
            const bar = bars[index % bars.length];
            const at = (beats) => start + beats * beat;

            // Chords: a long one on the first beat, a lighter one after the second.
            keys(bar.chord, at(0), beat * 3.4, 0.04);
            keys(bar.chord.slice(1), at(2.5), beat * 1.3, 0.025);

            note(hz(bar.bass), at(0), beat * 1.6, 0.16, "sine");
            note(hz(bar.bass), at(2.5), beat * 0.9, 0.12, "sine");

            kick(at(0));
            kick(at(2.5));
            hiss(at(1), 0.09, 0.05, "bandpass", 1800);
            hiss(at(3), 0.09, 0.05, "bandpass", 1800);
            // Hi-hats on every half beat, the off-beats a touch late and quieter.
            for (let half = 0; half < 8; half += 1) {
                const late = half % 2 ? beat * 0.08 : 0;
                hiss(at(half / 2) + late, 0.05, half % 2 ? 0.014 : 0.024, "highpass", 7000);
            }

            // The melody rests for four bars, then plays for four.
            if (Math.floor(index / bars.length) % 2 === 1) {
                bar.tune.forEach(([beats, value, length]) => {
                    note(hz(value), at(beats), beat * length, 0.05, "triangle");
                });
            }
        }

        let barIndex = 0;
        let nextBar = context.currentTime + 0.1;
        const timer = setInterval(() => {
            while (nextBar < context.currentTime + 0.5) {
                scheduleBar(barIndex, nextBar);
                barIndex += 1;
                nextBar += beat * 4;
            }
        }, 120);

        return {
            stop() {
                clearInterval(timer);
                master.gain.cancelScheduledValues(context.currentTime);
                master.gain.setValueAtTime(master.gain.value, context.currentTime);
                master.gain.exponentialRampToValueAtTime(0.0001, context.currentTime + 1);
                setTimeout(() => master.disconnect(), 1200);
            },
        };
    }

    function startMusic() {
        if (musicOn || !enabled || !context) {
            return;
        }
        musicOn = true;
        if (track) {
            startTrack();
        } else if (context.state === "running") {
            pad = startLoop();
        } else {
            // The sound engine is still waking up; this runs again when it is ready.
            musicOn = false;
        }
    }

    function stopMusic() {
        musicOn = false;
        if (track) {
            fadeTrack(0, () => track.pause());
        }
        if (pad) {
            pad.stop();
            pad = null;
        }
    }

    // One short tone that glides from one pitch to another and fades out.
    function tone(from, to, length, volume, shape) {
        const oscillator = context.createOscillator();
        const gain = context.createGain();
        const now = context.currentTime;
        oscillator.type = shape || "sine";
        oscillator.frequency.setValueAtTime(from, now);
        oscillator.frequency.exponentialRampToValueAtTime(to, now + length);
        gain.gain.setValueAtTime(volume, now);
        gain.gain.exponentialRampToValueAtTime(0.0001, now + length);
        oscillator.connect(gain).connect(context.destination);
        oscillator.start(now);
        oscillator.stop(now + length);
    }

    // A breath of filtered noise that sweeps upwards, used for wipes.
    function whoosh() {
        const length = 0.55;
        const now = context.currentTime;
        const buffer = context.createBuffer(1, context.sampleRate * length, context.sampleRate);
        const samples = buffer.getChannelData(0);
        for (let index = 0; index < samples.length; index += 1) {
            samples[index] = Math.random() * 2 - 1;
        }
        const noise = context.createBufferSource();
        const filter = context.createBiquadFilter();
        const gain = context.createGain();
        noise.buffer = buffer;
        filter.type = "bandpass";
        filter.Q.value = 0.9;
        filter.frequency.setValueAtTime(300, now);
        filter.frequency.exponentialRampToValueAtTime(2400, now + length);
        gain.gain.setValueAtTime(0.0001, now);
        gain.gain.exponentialRampToValueAtTime(0.07, now + length * 0.4);
        gain.gain.exponentialRampToValueAtTime(0.0001, now + length);
        noise.connect(filter).connect(gain).connect(context.destination);
        noise.start(now);
    }

    const sounds = {
        hover: () => tone(1500, 1100, 0.05, 0.025),
        click: () => {
            tone(520, 780, 0.09, 0.09, "triangle");
        },
        // Choosing a perfume, a collection or any other page: two rising notes.
        select: () => {
            tone(660, 990, 0.14, 0.14, "triangle");
            setTimeout(() => tone(1320, 1320, 0.16, 0.1, "sine"), 70);
        },
        on: () => {
            tone(520, 520, 0.12, 0.05, "triangle");
            setTimeout(() => tone(780, 780, 0.18, 0.05, "triangle"), 110);
        },
        whoosh,
    };

    function play(name) {
        if (!enabled || !context) {
            return;
        }
        // Still waking up after the first click: play as soon as it is ready.
        if (context.state !== "running") {
            context.resume().then(() => sounds[name]()).catch(() => {});
            return;
        }
        sounds[name]();
    }

    document.addEventListener("pointerdown", unlock, { capture: true });
    document.addEventListener("keydown", unlock, { capture: true });

    if (toggle) {
        toggle.addEventListener("click", () => {
            enabled = !enabled;
            try {
                localStorage.setItem("sound", enabled ? "on" : "off");
            } catch (error) {
                // The choice just won't be remembered.
            }
            showState();
            if (enabled) {
                unlock();
                play("on");
            } else {
                stopMusic();
            }
        });
    }

    // A click sound on anything pressable. A link to another page (a perfume,
    // a collection, the bag...) would normally leave before its sound could be
    // heard, so the page waits a moment for it and then goes.
    document.addEventListener("click", (event) => {
        const pressed = event.target.closest("a, button, .size-option, label.pay-option");
        if (!pressed || pressed === toggle) {
            return;
        }

        const leaves = pressed.matches("a[href]") && pressed.origin === location.origin
            && !(pressed.pathname === location.pathname && pressed.search === location.search && pressed.hash);
        if (!leaves) {
            play("click");
            return;
        }

        play("select");
        const ordinaryClick = event.button === 0 && !event.defaultPrevented && !pressed.target
            && !pressed.hasAttribute("download")
            && !(event.metaKey || event.ctrlKey || event.shiftKey || event.altKey);
        // Browsers using the dark slab between pages already pause long enough.
        if (enabled && context && ordinaryClick && !root.classList.contains("no-vt")) {
            event.preventDefault();
            setTimeout(() => {
                location.href = pressed.href;
            }, 240);
        }
    });

    // A faint tick as the mouse moves onto something pressable.
    if (hasMouse) {
        let last = null;
        document.addEventListener("mouseover", (event) => {
            const item = event.target.closest("a, button, .product-card");
            if (item && item !== last) {
                play("hover");
            }
            last = item;
        });
    }

    // Once a visitor has clicked somewhere on the site, browsers usually let
    // later pages make sound straight away, so try now rather than waiting.
    if (enabled) {
        try {
            context = new AudioContext();
        } catch (error) {
            context = null;
        }
    }

    // The music starts as soon as the browser lets the sound engine run.
    if (context) {
        context.addEventListener("statechange", startMusic);
        if (context.state === "running") {
            startMusic();
        }
    }

    showState();
    return { play };
})();

// ---- Intro ----
// base.html adds "intro" on the first page of a visit. The counter follows the
// page load, then the dark slab slides away and the page animates in.
if (root.classList.contains("intro")) {
    const counter = document.querySelector("[data-intro-count]");
    const bar = document.querySelector(".intro-bar i");
    const started = performance.now();
    const shortest = 1600;
    const longest = 5000;
    let pageLoaded = document.readyState === "complete";

    window.addEventListener("load", () => {
        pageLoaded = true;
    });

    function leaveIntro() {
        try {
            sessionStorage.setItem("introSeen", "1");
        } catch (error) {
            // Private browsing: the intro simply plays again next page.
        }
        root.classList.add("intro-leave");
        setTimeout(() => root.classList.remove("intro", "intro-leave"), 1200);
    }

    function count(now) {
        const elapsed = now - started;
        let progress = Math.min(elapsed / shortest, 1);
        // Hold just short of 100% until the page has really finished loading.
        if (!pageLoaded && elapsed < longest) {
            progress = Math.min(progress, 0.92);
        }
        counter.textContent = Math.round(progress * 100) + "%";
        bar.style.setProperty("--load", progress.toFixed(3));
        if (progress < 1) {
            requestAnimationFrame(count);
        } else {
            setTimeout(leaveIntro, 250);
        }
    }

    requestAnimationFrame(count);
}

// ---- Titles arrive letter by letter ----
// Each letter is wrapped so style.css can raise them one after another. Words
// stay whole so a title never breaks in the middle of one.
document.querySelectorAll(".page-head h1, .detail-copy h1, .auth-card h1, .slide-title").forEach((title) => {
    const text = title.textContent.trim();
    const words = text.split(/\s+/);
    let position = 0;

    title.setAttribute("aria-label", text);
    title.textContent = "";

    words.forEach((word, index) => {
        const wrap = document.createElement("span");
        wrap.className = "word";
        wrap.setAttribute("aria-hidden", "true");
        Array.from(word).forEach((letter) => {
            const cell = document.createElement("span");
            cell.className = "char";
            cell.textContent = letter;
            cell.style.setProperty("--c", position);
            position += 1;
            wrap.appendChild(cell);
        });
        title.appendChild(wrap);
        if (index < words.length - 1) {
            title.append(" ");
        }
    });
});

// ---- Navigation: a darker copy of each word is uncovered on a slant ----
document.querySelectorAll(".head-nav a").forEach((link) => {
    link.dataset.text = link.textContent.trim();
});

// ---- Sections fade in as they scroll into view ----
// Only items that start below the screen are hidden, so anything visible
// when the page opens can never be left blank.
if ("IntersectionObserver" in window) {
    const revealObserver = new IntersectionObserver((entries) => {
        entries.forEach((entry) => {
            if (entry.isIntersecting) {
                entry.target.classList.remove("reveal-wait");
                revealObserver.unobserve(entry.target);
            }
        });
    });

    document.querySelectorAll("[data-reveal]").forEach((item) => {
        if (item.getBoundingClientRect().top > window.innerHeight) {
            // Neighbours in the same row appear one after another.
            const position = Array.prototype.indexOf.call(item.parentElement.children, item);
            item.style.setProperty("--d", (position % 4) * 90 + "ms");
            item.classList.add("reveal-wait");
            revealObserver.observe(item);
        }
    });
}

// ---- Menu on small screens ----
const navToggle = document.querySelector(".nav-toggle");

function setMenu(isOpen) {
    root.classList.toggle("nav-open", isOpen);
    navToggle.setAttribute("aria-expanded", isOpen);
}

if (navToggle) {
    navToggle.addEventListener("click", () => setMenu(!root.classList.contains("nav-open")));

    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape" && root.classList.contains("nav-open")) {
            setMenu(false);
            navToggle.focus();
        }
    });
}

// ---- Message bar: its lines take turns ----
// The current line slides out upwards while the next slides in from below.
document.querySelectorAll("[data-banner]").forEach((banner) => {
    const lines = Array.from(banner.children);
    if (lines.length < 2) {
        return;
    }
    let showing = 0;
    setInterval(() => {
        const leaving = lines[showing];
        leaving.classList.remove("is-on");
        leaving.classList.add("is-off");
        setTimeout(() => leaving.classList.remove("is-off"), 700);
        showing = (showing + 1) % lines.length;
        lines[showing].classList.add("is-on");
    }, 5000);
});

// ---- Header: a soft shadow once the page has scrolled under it ----
const siteHeader = document.querySelector(".site-header");

if (siteHeader) {
    const markStuck = () => siteHeader.classList.toggle("is-stuck", window.scrollY > 31);
    window.addEventListener("scroll", markStuck, { passive: true });
    markStuck();
}

// ---- Search box: the hint types itself ----
// Runs only while the box is empty and not in use.
const searchInput = document.querySelector(".head-search input");

if (searchInput && !prefersReducedMotion) {
    const hints = ["Search for perfumes", "Search for notes", "Search for families"];
    let hint = 0;
    let length = hints[0].length;
    let erasing = true;

    function typeHint() {
        let wait = erasing ? 35 : 75;
        if (document.activeElement !== searchInput && !searchInput.value) {
            length += erasing ? -1 : 1;
            const stem = "Search for ".length;
            if (erasing && length <= stem) {
                erasing = false;
                hint = (hint + 1) % hints.length;
            } else if (!erasing && length >= hints[hint].length) {
                erasing = true;
                wait = 2400;
            }
            searchInput.placeholder = hints[hint].slice(0, length);
        }
        setTimeout(typeHint, wait);
    }

    setTimeout(typeHint, 2400);
}

// ---- Home slider ----
// Slides cross-fade. The line under the current caption fills as a timer and
// the slider moves on when it completes; hovering pauses it. Pointing at (or
// tabbing to) a caption brings up its slide, the arrow keys step through, and
// on touch screens a sideways swipe does the same. Each caption's description
// is typed out as its slide appears.
document.querySelectorAll("[data-slider]").forEach((slider) => {
    const slides = Array.from(slider.querySelectorAll("[data-slide]"));
    const tabs = Array.from(slider.querySelectorAll("[data-slide-tab]"));
    const dots = Array.from(slider.querySelectorAll(".slide-dots i"));
    const count = slides.length;
    if (count < 2) {
        return;
    }

    let current = 0;
    let typing = null;

    // Keep the full sentence for assistive technology and for retyping.
    const sentences = tabs.map((tab) => {
        const line = tab.querySelector(":scope > span");
        const text = line.textContent;
        tab.setAttribute("aria-label", tab.querySelector(".slide-title").textContent + ". " + text);
        return { line, text };
    });

    function typeOut(index) {
        clearInterval(typing);
        sentences.forEach((sentence) => {
            sentence.line.textContent = sentence.text;
        });
        if (prefersReducedMotion) {
            return;
        }
        const { line, text } = sentences[index];
        // Hold the caption's height so nothing jumps while it types.
        line.style.minHeight = line.offsetHeight + "px";
        let shown = 0;
        line.textContent = "";
        typing = setInterval(() => {
            shown += 1;
            line.textContent = text.slice(0, shown);
            if (shown >= text.length) {
                clearInterval(typing);
            }
        }, 28);
    }

    function show(index, byVisitor) {
        const next = (index + count) % count;
        if (next === current) {
            return;
        }
        if (byVisitor) {
            sound.play("whoosh");
        }
        // The outgoing slide stays underneath while the new one wipes over it.
        slides.forEach((slide, position) => slide.classList.toggle("is-prev", position === current));
        current = next;
        [slides, tabs, dots].forEach((group) => {
            group.forEach((item, position) => item.classList.toggle("is-on", position === current));
        });
        typeOut(current);
    }

    tabs.forEach((tab, index) => {
        tab.addEventListener("mouseenter", () => show(index, true));
        tab.addEventListener("focus", () => show(index, true));
        // The timer line is the caption's ::after; when it fills, move on.
        tab.addEventListener("animationend", (event) => {
            if (event.animationName === "slide-timer") {
                show(current + 1);
            }
        });
    });

    document.addEventListener("keydown", (event) => {
        if (event.target.closest("input, textarea, select")) {
            return;
        }
        if (event.key === "ArrowRight") {
            show(current + 1, true);
        } else if (event.key === "ArrowLeft") {
            show(current - 1, true);
        }
    });

    let touchStart = null;
    slider.addEventListener("touchstart", (event) => {
        touchStart = event.touches[0].clientX;
    }, { passive: true });
    slider.addEventListener("touchend", (event) => {
        const moved = event.changedTouches[0].clientX - touchStart;
        if (Math.abs(moved) > 50) {
            show(current + (moved < 0 ? 1 : -1), true);
        }
    }, { passive: true });

    typeOut(0);
});

// ---- Scroll-driven motion ----
// One pass per frame: the progress line across the top, and the home slider
// drifting more slowly than the page as it scrolls away.
if (!prefersReducedMotion) {
    const homeSlider = document.querySelector(".slider");
    const progressLine = document.createElement("div");
    let frameQueued = false;

    progressLine.className = "scroll-progress";
    progressLine.setAttribute("aria-hidden", "true");
    document.body.appendChild(progressLine);

    function updateScroll() {
        frameQueued = false;
        const furthest = document.documentElement.scrollHeight - window.innerHeight;
        const done = furthest > 0 ? Math.min(Math.max(window.scrollY / furthest, 0), 1) : 0;
        progressLine.style.transform = "scaleX(" + done + ")";
        if (homeSlider) {
            const away = Math.min(Math.max(window.scrollY / homeSlider.offsetHeight, 0), 1);
            homeSlider.style.setProperty("--away", away.toFixed(3));
        }
    }

    window.addEventListener("scroll", () => {
        if (!frameQueued) {
            frameQueued = true;
            requestAnimationFrame(updateScroll);
        }
    }, { passive: true });
    window.addEventListener("resize", updateScroll);
    updateScroll();
}

// ---- Smooth wheel scrolling ----
// The mouse wheel glides to its destination instead of jumping. Touch
// screens, the keyboard and the scrollbar keep their normal behaviour.
if (!prefersReducedMotion && hasMouse) {
    let destination = window.scrollY;
    let position = window.scrollY;
    let gliding = false;

    function scrollsOnItsOwn(element) {
        for (let node = element; node && node !== document.body; node = node.parentElement) {
            const overflow = getComputedStyle(node).overflowY;
            if ((overflow === "auto" || overflow === "scroll") && node.scrollHeight > node.clientHeight) {
                return true;
            }
        }
        return false;
    }

    function glide() {
        position += (destination - position) * 0.11;
        if (Math.abs(destination - position) < 0.5) {
            position = destination;
            gliding = false;
        }
        window.scrollTo({ top: position, behavior: "instant" });
        if (gliding) {
            requestAnimationFrame(glide);
        }
    }

    window.addEventListener("wheel", (event) => {
        const busy = root.classList.contains("intro");
        if (event.ctrlKey || busy || Math.abs(event.deltaX) > Math.abs(event.deltaY) || scrollsOnItsOwn(event.target)) {
            return;
        }
        event.preventDefault();

        const lineHeight = event.deltaMode === 1 ? 32 : event.deltaMode === 2 ? window.innerHeight : 1;
        const furthest = document.documentElement.scrollHeight - window.innerHeight;
        if (!gliding) {
            destination = position = window.scrollY;
        }
        destination = Math.min(Math.max(destination + event.deltaY * lineHeight, 0), furthest);
        if (!gliding) {
            gliding = true;
            requestAnimationFrame(glide);
        }
    }, { passive: false });
}

// ---- Pointer effects (mouse only) ----
if (!prefersReducedMotion && hasMouse) {
    // A dot trails the pointer. It grows over anything clickable, and over
    // pictures that open a perfume it becomes a small solid black dot.
    document.querySelectorAll(".slide, .slide-tab, .product-visual").forEach((item) => {
        item.dataset.cursor = "";
    });

    const cursor = document.createElement("div");
    const cursorLabel = document.createElement("span");
    cursor.className = "cursor";
    cursor.setAttribute("aria-hidden", "true");
    cursor.appendChild(cursorLabel);
    document.body.appendChild(cursor);

    let cursorX = 0;
    let cursorY = 0;
    let pointerX = 0;
    let pointerY = 0;
    let cursorShown = false;

    document.addEventListener("pointermove", (event) => {
        if (event.pointerType !== "mouse") {
            return;
        }
        pointerX = event.clientX;
        pointerY = event.clientY;
        if (!cursorShown) {
            cursorShown = true;
            cursorX = pointerX;
            cursorY = pointerY;
            cursor.classList.add("is-visible");
        }
        const labelled = event.target.closest("[data-cursor]");
        cursorLabel.textContent = labelled ? labelled.dataset.cursor : "";
        cursor.classList.toggle("is-label", Boolean(labelled));
        cursor.classList.toggle("is-link", !labelled && Boolean(event.target.closest("a, button, select, label, input")));
    });

    document.documentElement.addEventListener("mouseleave", () => {
        cursorShown = false;
        cursor.classList.remove("is-visible");
    });
    document.addEventListener("mousedown", () => cursor.classList.add("is-down"));
    document.addEventListener("mouseup", () => cursor.classList.remove("is-down"));

    (function follow() {
        cursorX += (pointerX - cursorX) * 0.22;
        cursorY += (pointerY - cursorY) * 0.22;
        cursor.style.translate = cursorX.toFixed(1) + "px " + cursorY.toFixed(1) + "px";
        requestAnimationFrame(follow);
    })();

    // Perfume pictures tilt towards the pointer.
    document.querySelectorAll(".product-card").forEach((card) => {
        const visual = card.querySelector(".product-visual");

        card.addEventListener("pointermove", (event) => {
            const box = visual.getBoundingClientRect();
            const across = (event.clientX - box.left) / box.width - 0.5;
            const down = (event.clientY - box.top) / box.height - 0.5;
            visual.style.setProperty("--tilt-y", (across * 9).toFixed(2) + "deg");
            visual.style.setProperty("--tilt-x", (-down * 9).toFixed(2) + "deg");
        });
        card.addEventListener("pointerleave", () => {
            visual.style.removeProperty("--tilt-x");
            visual.style.removeProperty("--tilt-y");
        });
    });
}

// ---- Checkout: the button says what happens next ----
const placeOrderButton = document.querySelector("[data-place-order]");

if (placeOrderButton) {
    const choices = document.querySelectorAll('input[name="payment_method"]');

    function nameButton() {
        const chosen = document.querySelector('input[name="payment_method"]:checked');
        placeOrderButton.textContent = chosen && chosen.value !== "cod" ? "Continue to payment" : "Place order";
    }

    choices.forEach((choice) => choice.addEventListener("change", nameButton));
    nameButton();
}

// ---- Toast messages fade out on their own ----
document.querySelectorAll(".message").forEach((message) => {
    setTimeout(() => {
        message.classList.add("is-leaving");
        setTimeout(() => message.remove(), 400);
    }, 5000);
});

// ---- Filters that apply as soon as they change ----
document.querySelectorAll("select[data-autosubmit]").forEach((select) => {
    select.addEventListener("change", () => select.form.submit());
});

// ---- Quantity steppers (product page and bag) ----
document.querySelectorAll("[data-stepper]").forEach((stepper) => {
    const input = stepper.querySelector("input");

    function setQuantity(quantity) {
        const min = Number(input.min || 0);
        const max = Number(input.max || Infinity);
        const clamped = Math.min(Math.max(quantity, min), max);

        if (clamped === Number(input.value)) {
            return;
        }
        input.value = clamped;
        // In the bag, a new quantity is saved straight away.
        if (stepper.hasAttribute("data-autosubmit")) {
            input.form.submit();
        }
    }

    stepper.querySelectorAll("[data-step]").forEach((button) => {
        button.addEventListener("click", () => {
            setQuantity(Number(input.value || 0) + Number(button.dataset.step));
        });
    });

    if (stepper.hasAttribute("data-autosubmit")) {
        input.addEventListener("change", () => input.form.submit());
    }
});

// ---- Product page: choosing a bottle size ----
const addForm = document.getElementById("add-to-cart-form");

if (addForm) {
    const sizeButtons = document.querySelectorAll(".size-option:not(:disabled)");
    const priceElement = document.getElementById("selected-price");
    const sizeLabel = document.getElementById("selected-size-label");
    const stockMessage = document.getElementById("stock-message");
    const quantityInput = document.getElementById("quantity");

    // When a size is clicked, update the displayed price and the cart variant.
    sizeButtons.forEach((button) => {
        button.addEventListener("click", () => {
            sizeButtons.forEach((item) => {
                item.classList.remove("selected");
                item.setAttribute("aria-pressed", "false");
            });
            button.classList.add("selected");
            button.setAttribute("aria-pressed", "true");

            const { variantId, volume, price, oldPrice, discount } = button.dataset;
            const stock = Number(button.dataset.stock);

            priceElement.textContent = "";
            const current = document.createElement("span");
            current.textContent = formatPrice(price);
            priceElement.appendChild(current);

            if (oldPrice) {
                const previous = document.createElement("del");
                previous.textContent = formatPrice(oldPrice);
                const saving = document.createElement("em");
                saving.textContent = "Save " + discount + "%";
                priceElement.append(previous, saving);
            }

            sizeLabel.textContent = volume + " ml";
            stockMessage.textContent = stock <= 3 ? "Only " + stock + " left" : "In stock";
            stockMessage.classList.toggle("low", stock <= 3);

            // The quantity can never exceed what is in stock for this size.
            quantityInput.max = stock;
            if (Number(quantityInput.value) > stock) {
                quantityInput.value = stock;
            }

            // The URL contains the selected variant ID so the correct price/stock is used.
            addForm.action = addForm.dataset.urlTemplate.replace("/0/", "/" + variantId + "/");
        });
    });
}

// ---- Moving between pages ----
// Modern browsers animate page changes from CSS alone: the new page arrives
// behind a slanted edge (see "@view-transition" in style.css). Choosing a
// perfume names its picture so that it travels from the card to the product
// page.
document.addEventListener("click", (event) => {
    const link = event.target.closest(".product-card a");
    if (!link) {
        return;
    }
    // Only one picture on the page may carry the name at a time.
    const current = document.querySelector(".detail-visual");
    if (current) {
        current.style.viewTransitionName = "none";
    }
    document.querySelectorAll(".product-visual").forEach((visual) => {
        visual.style.viewTransitionName = "";
    });
    link.closest(".product-card").querySelector(".product-visual").style.viewTransitionName = "product-hero";
});

// Other browsers get a dark slab that sweeps across before the next page loads.
if (!("CSSViewTransitionRule" in window) && !prefersReducedMotion) {
    root.classList.add("no-vt");

    const curtain = document.createElement("div");
    curtain.className = "page-curtain";
    document.body.appendChild(curtain);

    document.addEventListener("click", (event) => {
        const link = event.target.closest("a[href]");
        if (!link || event.defaultPrevented || event.button !== 0) {
            return;
        }
        if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) {
            return;
        }
        if (link.target || link.hasAttribute("download") || link.origin !== location.origin) {
            return;
        }
        // Links to another part of the same page just scroll.
        if (link.pathname === location.pathname && link.search === location.search && link.hash) {
            return;
        }

        event.preventDefault();
        root.classList.add("is-leaving");
        setTimeout(() => {
            location.href = link.href;
        }, 500);
    });
}

// Coming back with the browser's Back button restores the page as it was left.
window.addEventListener("pageshow", (event) => {
    if (!event.persisted) {
        return;
    }
    root.classList.remove("is-leaving");
    document.querySelectorAll(".product-visual, .detail-visual").forEach((visual) => {
        visual.style.viewTransitionName = "";
    });
});
