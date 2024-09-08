(function($) {
    django.jQuery(document).ready(function() {
        // Override the calendar's default settings
        $.datepicker.setDefaults({
            firstDay: 1  // 0 = Sunday, 1 = Monday
        });
    });
})(django.jQuery);