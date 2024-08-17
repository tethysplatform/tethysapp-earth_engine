EE_PRODUCTS = {
    'modis': {
        'terra': {
            'snow': {
                'display': 'Snow Cover Daily Global 500m',
                'collection': 'MODIS/061/MOD10A1',
                'index': 'NDSI_Snow_Cover',
                'vis_params': {
                    'min': 0.0,
                    'max': 100.0,
                    'palette': ['black', '0dffff', '0524ff', 'ffffff'],
                },
                'start_date': '2000-02-24',
                'end_date': None  # to present
            },
            'temperature': {
                'display': 'Land Surface Temperature and Emissivity Daily Global 1km',
                'collection': 'MODIS/061/MOD11A1',
                'index': 'LST_Day_1km',
                'vis_params': {
                    'min': 13000.0,
                    'max': 16500.0,
                    'palette': [
                        '040274', '040281', '0502a3', '0502b8', '0502ce', '0502e6',
                        '0602ff', '235cb1', '307ef3', '269db1', '30c8e2', '32d3ef',
                        '3be285', '3ff38f', '86e26f', '3ae237', 'b5e22e', 'd6e21f',
                        'fff705', 'ffd611', 'ffb613', 'ff8b13', 'ff6e08', 'ff500d',
                        'ff0000', 'de0101', 'c21301', 'a71001', '911003'
                    ],
                },
                'start_date': '2000-03-05',
                'end_date': None  # to present
            }
        },
    },
    'sentinel': {
        '5': {
            'cloud': {
                'display': 'Cloud',
                'collection': 'COPERNICUS/S5P/OFFL/L3_CLOUD',
                'index': 'cloud_fraction',
                'vis_params': {
                    'min': 0,
                    'max': 0.95,
                    'palette': ['black', 'blue', 'purple', 'cyan', 'green', 'yellow', 'red']
                },
                'start_date': '2018-07-04',
                'end_date': None  # to present
            },
            'co': {
                'display': 'Carbon Monoxide',
                'collection': 'COPERNICUS/S5P/OFFL/L3_CO',
                'index': 'CO_column_number_density',
                'vis_params': {
                    'min': 0,
                    'max': 0.05,
                    'palette': ['black', 'blue', 'purple', 'cyan', 'green', 'yellow', 'red']
                },
                'start_date': '2018-06-28',
                'end_date': None  # to present
            },
            'ozone': {
                'display': 'Ozone',
                'collection': 'COPERNICUS/S5P/OFFL/L3_O3',
                'index': 'O3_column_number_density',
                'vis_params': {
                    'min': 0.12,
                    'max': 0.15,
                    'palette': ['black', 'blue', 'purple', 'cyan', 'green', 'yellow', 'red']
                },
                'start_date': '2018-09-08',
                'end_date': None  # to present
            },
            'so2': {
                'display': 'Sulphur Dioxide',
                'collection': 'COPERNICUS/S5P/OFFL/L3_SO2',
                'index': 'SO2_column_number_density',
                'vis_params': {
                    'min': 0.0,
                    'max': 0.0005,
                    'palette': ['black', 'blue', 'purple', 'cyan', 'green', 'yellow', 'red']
                },
                'start_date': '2018-12-05',
                'end_date': None  # to present
            },
            'ch4': {
                'display': 'Methane',
                'collection': 'COPERNICUS/S5P/OFFL/L3_CH4',
                'index': 'CH4_column_volume_mixing_ratio_dry_air',
                'vis_params': {
                    'min': 1750,
                    'max': 1900,
                    'palette': ['black', 'blue', 'purple', 'cyan', 'green', 'yellow', 'red']
                },
                'start_date': '2019-02-08',
                'end_date': None  # to present
            },
        }
    },
    'landsat': {
        '8': {
            'surface': {
                'display': 'Surface Reflectance',
                'collection': 'LANDSAT/LC08/C02/T1_L2',
                'index': None,
                'vis_params': {
                    'bands': ['SR_B4', 'SR_B3', 'SR_B2'],
                    'min': 0,
                    'max': 3000,
                    'gamma': 1.4,
                },
                'cloud_mask': 'mask_l8_sr',
                'start_date': '2013-04-01',
                'end_date': None  # to present
            },
            'toa': {
                'display': 'Top-of-Atmosphere(TOA) Reflectance',
                'collection': 'LANDSAT/LC08/C02/T1_TOA', 
                'index': None,
                'vis_params': {
                    'bands': ['B4', 'B3', 'B2'],
                    'min': 0,
                    'max': 3000,
                    'gamma': 1.4,
                },
                'start_date': '2013-04-01',
                'end_date': None  # to present
            },
        },
        '9': {
            'surface': {
                'display': 'Surface Reflectance',
                'collection': 'LANDSAT/LC09/C02/T1_L2',
                'index': None,
                'vis_params': {
                    'bands': ['SR_B4', 'SR_B3', 'SR_B2'],
                    'min': 0,
                    'max': 3000,
                    'gamma': 1.4,
                },
                'cloud_mask': 'mask_l8_sr',
                'start_date': '2021-10-31',
                'end_date': None  # to present
            },
            'toa': {
                'display': 'Top-of-Atmosphere(TOA) Reflectance',
                'collection': 'LANDSAT/LC09/C02/T1_TOA', 
                'index': None,
                'vis_params': {
                    'bands': ['B4', 'B3', 'B2'],
                    'min': 0,
                    'max': 3000,
                    'gamma': 1.4,
                },
                'start_date': '2021-10-31',
                'end_date': None  # to present
            },
        }
    }
}