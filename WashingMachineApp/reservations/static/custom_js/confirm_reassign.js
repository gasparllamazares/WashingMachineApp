document.addEventListener('DOMContentLoaded', function () {
    const individualSelect = document.querySelector('select[name="individuals"]');
    const assignedIndividuals = JSON.parse(individualSelect.dataset.assignedIndividuals || '[]');

    individualSelect.addEventListener('change', function () {
        const selectedOptions = Array.from(this.selectedOptions);
        selectedOptions.forEach(option => {
            if (assignedIndividuals.includes(option.value)) {
                const confirmed = confirm(option.text + " is already assigned to another room. Do you want to reassign them?");
                if (!confirmed) {
                    // Unselect the option if the user cancels the reassignment
                    option.selected = false;
                }
            }
        });
    });
});