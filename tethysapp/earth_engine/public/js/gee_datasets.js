var GEE_DATASETS = (function() {
    // Wrap the library in a package function
    "use strict"; // And enable strict mode for this library

    /************************************************************************
    *                      MODULE LEVEL / GLOBAL VARIABLES
    *************************************************************************/
    var MODIS = 'modis',
        SENTINEL = 'sentinel',
        LANDSAT = 'landsat',
        INITIAL_START_DATE,
        INITIAL_END_DATE,
        EE_PRODUCTS;

    var public_interface;

    // Selector Variables
    var m_platform,
        m_sensor,
        m_product,
        m_start_date,
        m_end_date,
        m_reducer;

    // Map Variables
    var m_map,
        m_gee_layer;

    /************************************************************************
    *                    PRIVATE FUNCTION DECLARATIONS
    *************************************************************************/
    // Dataset Select Methods
    var bind_controls, update_product_options, update_sensor_options, update_date_bounds, collect_data;

    // Map Methods
    var update_map, update_data_layer, create_data_layer, clear_map;

    // Time Series Plot Methods
    var get_geometry, update_plot, show_plot_modal;

    /************************************************************************
    *                    PRIVATE FUNCTION IMPLEMENTATIONS
    *************************************************************************/
    // Dataset Select Methods
    bind_controls = function() {
        $('#platform').on('change', function() {
            let platform = $('#platform').val();

            if (platform !== m_platform) {
                m_platform = platform;
                console.log(`Platform Changed to: ${m_platform}`);
                // Update the sensor options when platform changes
                update_sensor_options();
            }
        });

        $('#sensor').on('change', function() {
            let sensor = $('#sensor').val();

            if (sensor !== m_sensor) {
                m_sensor = sensor;
                console.log(`Sensor Changed to: ${m_sensor}`);
                // Update the product options when sensor changes
                update_product_options();
            }
        });

        $('#product').on('change', function() {
            let product = $('#product').val();

            if (product !== m_product) {
                m_product = product;
                console.log(`Product Changed to: ${m_product}`);
                // Update the valid date range when product changes
                update_date_bounds();
            }
        });


        $('#start_date').on('change', function() {
            let start_date = $('#start_date').val();

            if (start_date !== m_start_date) {
                m_start_date = start_date;
                console.log(`Start Date Changed to: ${m_start_date}`);
            }
        });

        $('#end_date').on('change', function() {
            let end_date = $('#end_date').val();

            if (end_date !== m_end_date) {
                m_end_date = end_date;
                console.log(`End Date Changed to: ${m_end_date}`);
            }
        });

        $('#reducer').on('change', function() {
            let reducer = $('#reducer').val();

            if (reducer !== m_reducer) {
                m_reducer = reducer;
                console.log(`Reducer Changed to: ${m_reducer}`);
            }
        });

        $('#load_map').on('click', function() {
            update_map();
        });

        $('#clear_map').on('click', function() {
            clear_map();
        });

        $('#load_plot').on('click', function() {
            update_plot();
        });
    };

    update_sensor_options = function() {
        if (!m_platform in EE_PRODUCTS) {
            alert('Unknown platform selected.');
        }

        // Clear sensor options
        $('#sensor').select2().empty();

        // Set the Sensor Options
        let first_option = true;
        for (var sensor in EE_PRODUCTS[m_platform]) {
            let sensor_display_name = sensor.toUpperCase();
            let new_option = new Option(sensor_display_name, sensor, first_option, first_option);
            $('#sensor').append(new_option);
            first_option = false;
        }

        // Trigger a sensor change event to update select box
        $('#sensor').trigger('change');
        update_date_bounds();
    };

    update_product_options = function() {
        if (!m_platform in EE_PRODUCTS || !m_sensor in EE_PRODUCTS[m_platform]) {
            alert('Unknown platform or sensor selected.');
        }

        // Clear product options
        $('#product').select2().empty();

        let first_option = true;

        // Set the Product Options
        for (var product in EE_PRODUCTS[m_platform][m_sensor]) {
            let product_display_name = EE_PRODUCTS[m_platform][m_sensor][product]['display'];
            let new_option = new Option(product_display_name, product, first_option, first_option);
            $('#product').append(new_option);
            first_option = false;
        }

        // Trigger a product change event to update select box
        $('#product').trigger('change');
        update_date_bounds();
    };

    update_date_bounds = function() {
        // Get new date picker bounds for the current product
        let earliest_valid_date = EE_PRODUCTS[m_platform][m_sensor][m_product]['start_date'];
        let latest_valid_date = EE_PRODUCTS[m_platform][m_sensor][m_product]['end_date'];

        // Get current values of date pickers
        let current_start_date = $('#start_date').val();
        let current_end_date = $('#end_date').val();

        // Convert to Dates objects for comparison
        let date_evd = Date.parse(earliest_valid_date);
        let date_lvd = Date.parse(latest_valid_date) ? (latest_valid_date) : Date.now();
        let date_csd = Date.parse(current_start_date);
        let date_ced = Date.parse(current_end_date);

        // Don't reset currently selected dates if they fall within the new date range
        let reset_current_dates = true;

        if (date_csd >= date_evd && date_csd <= date_lvd && date_ced >= date_evd && date_ced <= date_lvd) {
            reset_current_dates = false;
        }

        // Update start date datepicker bounds
        $('#start_date').datepicker('setStartDate', earliest_valid_date);
        $('#start_date').datepicker('setEndDate', latest_valid_date);
        if (reset_current_dates) {
            $('#start_date').datepicker('update', INITIAL_START_DATE);
            m_start_date = INITIAL_START_DATE;
        }

        // Update end date datepicker bounds
        $('#end_date').datepicker('setStartDate', earliest_valid_date);
        $('#end_date').datepicker('setEndDate', latest_valid_date);
        if (reset_current_dates) {
            $('#end_date').datepicker('update', INITIAL_END_DATE);
            m_end_date = INITIAL_END_DATE;
        }

        console.log('Date Bounds Changed To: ' + earliest_valid_date + ' - ' + latest_valid_date);
    };

    collect_data = function() {
        let data = {
            platform: m_platform,
            sensor: m_sensor,
            product: m_product,
            start_date: m_start_date,
            end_date: m_end_date,
            reducer: m_reducer,
            geometry: get_geometry()
        };
        return data;
    };

    // Map Methods
    update_map = function() {
        let data = collect_data();

        let xhr = $.ajax({
            type: 'POST',
            url: 'get-image-collection/',
            dataType: 'json',
            data: data
        });

        xhr.done(function(response) {
            if (response.success) {
                console.log(response.url);
                update_data_layer(response.url);
            } else {
                alert('Oops, there was a problem loading the map you requested. Please try again.');
            }
        });
    };

    update_data_layer = function(url) {
        if (!m_gee_layer) {
            create_data_layer(url);
        } else {
            m_gee_layer.getSource().setUrl(url);
        }
    };

    create_data_layer = function(url) {
        let source = new ol.source.XYZ({
            url: url,
            attributions: '<a href="https://earthengine.google.com" target="_">Google Earth Engine</a>'
        });

        source.on('tileloadstart', function() {
            $('#loader').addClass('show');
        });

        source.on('tileloadend', function() {
            $('#loader').removeClass('show');
        });

        source.on('tileloaderror', function() {
            $('#loader').removeClass('show');
        });

        m_gee_layer = new ol.layer.Tile({
            source: source,
            opacity: 0.7
        });

        // Insert below the draw layer (so drawn polygons and points render on top of data layer).
        m_map.getLayers().insertAt(1, m_gee_layer);
    };

    clear_map = function() {
        if (m_gee_layer) {
            m_map.removeLayer(m_gee_layer);
            m_gee_layer = null;
        }
    };

    // Time Series Plot Methods
    get_geometry = function() {
        // Get drawn geometry from embedded textarea of Tethys Map View
        let geometry_json = $('#map_view_geometry').val() || null;
        return geometry_json;
    };

    update_plot = function() {
        let data = collect_data();

        show_plot_modal();

        $('#plot-container').load('get-time-series-plot/', data);
    };

    show_plot_modal = function() {
        $('#plot-container').html(
            '<div id="plot-loader">' +
                '<img src="/static/earth_engine/images/plot-loader.gif">' +
                '<p>Loading... This may take up to 5 minutes. Please wait.</p>' +
            '</div>'
        );
        $('#plot-modal').modal('show');
    };

    /************************************************************************
    *                            PUBLIC INTERFACE
    *************************************************************************/
    public_interface = {};

   /************************************************************************
    *                  INITIALIZATION / CONSTRUCTOR
    *************************************************************************/
    $(function() {
        // Initialize Global Variables
        bind_controls();

        // EE Products
        EE_PRODUCTS = $('#ee-products').data('ee-products');

        // Initialize values
        m_platform = $('#platform').val();
        m_sensor = $('#sensor').val();
        m_product = $('#product').val();
        INITIAL_START_DATE = m_start_date = $('#start_date').val();
        INITIAL_END_DATE = m_end_date = $('#end_date').val();
        m_reducer = $('#reducer').val();

        m_map = TETHYS_MAP_VIEW.getMap();

        // Open boundary file modal if it has an error
        if ($('#boundary-file-form-group').hasClass('has-error')) {
            $('#set-boundary-modal').modal('show');
        }
    });

    return public_interface;

}()); // End of package wrapper
