// Small enhancements for the FragranSoul storefront.
// Every page works without this file; it only makes things smoother.

const root = document.documentElement;
root.classList.add("js");

const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
const hasMouse = window.matchMedia("(hover: hover) and (pointer: fine)").matches;

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

    function show(index) {
        const next = (index + count) % count;
        if (next === current) {
            return;
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
        tab.addEventListener("mouseenter", () => show(index));
        tab.addEventListener("focus", () => show(index));
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
            show(current + 1);
        } else if (event.key === "ArrowLeft") {
            show(current - 1);
        }
    });

    let touchStart = null;
    slider.addEventListener("touchstart", (event) => {
        touchStart = event.touches[0].clientX;
    }, { passive: true });
    slider.addEventListener("touchend", (event) => {
        const moved = event.changedTouches[0].clientX - touchStart;
        if (Math.abs(moved) > 50) {
            show(current + (moved < 0 ? 1 : -1));
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
    // pictures that open a perfume it becomes a round "View" label.
    document.querySelectorAll(".slide, .slide-tab, .product-visual").forEach((item) => {
        item.dataset.cursor = "View";
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
