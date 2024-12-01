/**
 * Initializes the slideshow functionality when the DOM content is loaded.
 * Automatically cycles through slides and adds pause/resume functionality on hover.
 */
document.addEventListener("DOMContentLoaded", () => {
    /**
     * Current index of the visible slide.
     * @type {number}
     */
    let slideIndex = 0;

    /**
     * Collection of all slide elements in the DOM.
     * @type {HTMLCollectionOf<Element>}
     */
    const slides = document.getElementsByClassName("slide");

    /**
     * Displays the current slide and hides all others.
     * Automatically advances to the next slide every 5 seconds.
     */
    function showSlides() {
        // Hide all slides
        for (let i = 0; i < slides.length; i++) {
            slides[i].style.display = "none";
        }

        // Increment slide index
        slideIndex++;
        if (slideIndex > slides.length) slideIndex = 1; // Loop back to the first slide

        // Display the current slide
        slides[slideIndex - 1].style.display = "block";

        // Set a timeout to display the next slide
        setTimeout(showSlides, 5000);
    }

    // Display the first slide initially
    slides[slideIndex].style.display = "block";

    // Start the slideshow
    showSlides();

    /**
     * ID of the timeout used to cycle through slides.
     * @type {number | undefined}
     */
    let timeoutId;

    // Add hover event listeners to pause and resume the slideshow
    for (let i = 0; i < slides.length; i++) {
        slides[i].addEventListener("mouseenter", () => clearTimeout(timeoutId));
        slides[i].addEventListener("mouseleave", () => {
            timeoutId = setTimeout(showSlides, 5000);
        });
    }
});

