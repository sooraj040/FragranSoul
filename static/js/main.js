// Small enhancements for the FragranSoul storefront.
// Every page works without this file; it only makes things smoother.

document.documentElement.classList.add("js");

// Format prices consistently with the Indian Rupee symbol.
function formatPrice(value) {
    return "₹" + Number(value).toLocaleString("en-IN", {
        minimumFractionDigits: 0,
        maximumFractionDigits: 2,
    });
}

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
            item.classList.add("reveal-wait");
            revealObserver.observe(item);
        }
    });
}

// ---- Mobile menu ----
const header = document.querySelector(".site-header");
const navToggle = document.querySelector(".nav-toggle");

if (header && navToggle) {
    navToggle.addEventListener("click", () => {
        const isOpen = header.classList.toggle("nav-open");
        navToggle.setAttribute("aria-expanded", isOpen);
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
