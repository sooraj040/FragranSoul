// Small enhancements for the FragranSoul storefront.
// Every page works without this file; it only makes things smoother.

const root = document.documentElement;
root.classList.add("js");

const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

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
document.querySelectorAll("[data-banner]").forEach((banner) => {
    const lines = Array.from(banner.children);
    if (lines.length < 2) {
        return;
    }
    let showing = 0;
    setInterval(() => {
        lines[showing].classList.remove("is-on");
        showing = (showing + 1) % lines.length;
        lines[showing].classList.add("is-on");
    }, 5000);
});

// ---- Home slider ----
// Slides cross-fade on their own every few seconds. Pointing at (or tabbing
// to) a caption brings up its slide, and on touch screens a sideways swipe
// moves between them.
document.querySelectorAll("[data-slider]").forEach((slider) => {
    const groups = [
        Array.from(slider.querySelectorAll("[data-slide]")),
        Array.from(slider.querySelectorAll("[data-slide-tab]")),
        Array.from(slider.querySelectorAll(".slide-dots i")),
    ];
    const count = groups[0].length;
    if (count < 2) {
        return;
    }

    let current = 0;
    let timer = null;

    function show(index) {
        current = (index + count) % count;
        groups.forEach((group) => {
            group.forEach((item, position) => item.classList.toggle("is-on", position === current));
        });
    }

    function stop() {
        clearInterval(timer);
    }

    function play() {
        stop();
        if (!prefersReducedMotion) {
            timer = setInterval(() => show(current + 1), 6000);
        }
    }

    groups[1].forEach((tab, index) => {
        tab.addEventListener("mouseenter", () => show(index));
        tab.addEventListener("focus", () => show(index));
    });
    slider.addEventListener("mouseenter", stop);
    slider.addEventListener("mouseleave", play);

    let touchStart = null;
    slider.addEventListener("touchstart", (event) => {
        touchStart = event.touches[0].clientX;
        stop();
    }, { passive: true });
    slider.addEventListener("touchend", (event) => {
        const moved = event.changedTouches[0].clientX - touchStart;
        if (Math.abs(moved) > 50) {
            show(current + (moved < 0 ? 1 : -1));
        }
        play();
    }, { passive: true });

    play();
});

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
// Modern browsers cross-fade page changes from CSS alone (see
// "@view-transition" in style.css). Choosing a perfume names its picture so
// that it travels from the card to the product page.
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

// Coming back with the browser's Back button restores the page as it was left.
window.addEventListener("pageshow", (event) => {
    if (!event.persisted) {
        return;
    }
    document.querySelectorAll(".product-visual, .detail-visual").forEach((visual) => {
        visual.style.viewTransitionName = "";
    });
});
