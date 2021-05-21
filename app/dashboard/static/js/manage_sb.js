var displayEmojiTrigger;
var picker;

var currentOnClick;

$(document).ready(() => {
    displayEmojiTrigger = document.querySelector("#display_emoji");
    displayEmojiTrigger.addEventListener("click", () => {togglePicker(); currentOnClick = setDisplayEmoji})

    picker = document.querySelector("emoji-picker");
    picker.addEventListener("emoji-click", event => {togglePicker(); currentOnClick(event.detail.emoji.unicode)});
})

function setDisplayEmoji(emojiUnicode) {
    displayEmojiTrigger.textContent = emojiUnicode;
}

function togglePicker() {
    if (picker.classList.contains("hidden")) {
        picker.classList.remove("hidden");
    } else {
        picker.classList.add("hidden");
    }
}