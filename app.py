from flask import Flask, render_template, send_file, request, render_template_string,flash
import ezdxf
import os
import numpy as np
import sys
import matplotlib.pyplot as plt

app = Flask(__name__)
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generate_dxf', methods=['POST'])
def generate_dxf():
    import ezdxf
    from ezdxf import units
    from ezdxf.math import Vec2
    from ezdxf.render import mleader
    import math

    beam_type = request.form['type']
    print(beam_type)
    if beam_type == "Cantilever":
        beam_length = float(request.form['beam_length'])
        clear_span = beam_length
        exposure = request.form['exposure']
        cd = 750
        wall_thickness = float(request.form['wall_thickness'])
        span_d = 4
        fck = int(request.form['fck'])
        fy = int(request.form['fy'])
        # ------------------step-1-------------geometery
        effective_length = clear_span + cd / 2000
        if (beam_length>10):
            return("For cantilever over 10m ,this tool is not valid")
            sys.exit()
        def get_nominal_cover(exposure_condition):
            covers = {
                "Mild": 20,
                "Moderate": 30,
                "Severe": 45,
                "Very severe": 50,
                "Extreme": 75
            }
            return covers.get(exposure_condition, "Exposure not found")

        md = 32
        bt = 8
        nominal_cover = get_nominal_cover(exposure)
        ed = effective_length * 1000 / span_d
        ed1 = effective_length * 1000 / span_d + bt + md / 2 + nominal_cover
        provided_depth = math.ceil(ed1 / 25) * 25
        print("provide Overall depth", provided_depth, "mm")
        effective_depth = provided_depth - nominal_cover - md / 2 - bt
        print("revised Effective depth", effective_depth, "mm")
        revised_effective_length = clear_span * 1000 + effective_depth / 2
        print("revised Effective Length: ", revised_effective_length, "mm")
        # -----------------------Step-2---------------------------------------------
        self_weight = provided_depth * wall_thickness * 25 / (10 ** 6)

        def get_point_loads():
            point_loads = []
            num_point_loads = 0
            for i in range(1, num_point_loads + 1):
                magnitude = float(request.form[f'magnitude_{i}'])
                position = float(request.form[f'position_{i}'])
                point_loads.append((magnitude, position))

            return f"Point loads: {point_loads}"

        def get_tcmax(concrete_grade):
            # Dictionary containing the tcmax values for different concrete grades
            tcmax_values = {
                15: 2.5,
                20: 2.8,
                25: 3.1,
                30: 3.5,
                35: 3.7,
                40: 4.0
            }

            # Return the tcmax value for the given concrete grade
            return tcmax_values.get(concrete_grade, "Grade not found")

        # this would be user input in practice
        tcmax = get_tcmax(fck)

        def calculate_sf_bm(point_loads, udl, beam_length):
            x = np.linspace(0, beam_length, 500)
            sf = np.zeros_like(x)
            bm = np.zeros_like(x)

            # Add effects of UDL
            udl_mag, udl_start, udl_end = udl, 0, revised_effective_length
            for i, xi in enumerate(x):
                if xi >= udl_start and xi <= udl_end:
                    sf[i] -= udl_mag * (xi - udl_start)
                    bm[i] -= udl_mag * (xi - udl_start) ** 2 / 2

            # Add effects of point loads
            for magnitude, position in point_loads:
                for i, xi in enumerate(x):
                    if xi >= position:
                        sf[i] -= magnitude
                        bm[i] -= magnitude * (xi - position)

            # Find the maximum absolute SF and the maximum BM (ignoring the sign for SF)
            max_sf = np.max(np.abs(sf))
            max_sf_value = max(sf[np.argmax(np.abs(sf))], sf[np.argmin(sf)],
                               key=abs)  # This ensures we get the value with its original sign
            max_bm = np.max(np.abs(bm))
            max_bm_value = max(bm[np.argmax(bm)], bm[np.argmin(bm)],
                               key=abs)  # This ensures we get the value with its original sign

            return x, sf, bm, max_sf_value, max_bm_value

        def plot_sf_bm(x, sf, bm, max_sf_value, max_bm_value):
            fig, axs = plt.subplots(2, 1, figsize=(10, 8))

            # Shear Force plot
            axs[0].plot(x, sf, label="Shear Force", color='blue')
            axs[0].set_ylabel('Shear Force (N)')
            axs[0].grid(True)
            max_sf_x = x[np.argmax(np.abs(sf))]  # Position of max SF
            axs[0].annotate(f'Max SF: {max_sf_value} N', xy=(max_sf_x, max_sf_value),
                            xytext=(max_sf_x, max_sf_value * 1.1),
                            arrowprops=dict(facecolor='black', shrink=0.05))
            axs[0].legend()

            # Bending Moment plot
            axs[1].plot(x, bm, label="Bending Moment", color='red')
            axs[1].set_ylabel('Bending Moment (N.m)')
            axs[1].set_xlabel('Position along beam (m)')
            axs[1].grid(True)
            max_bm_x = x[np.argmax(np.abs(bm))]  # Position of max BM
            axs[1].annotate(f'Max BM: {max_bm_value} N.m', xy=(max_bm_x, max_bm_value),
                            xytext=(max_bm_x, max_bm_value * 1.1),
                            arrowprops=dict(facecolor='black', shrink=0.05))
            axs[1].legend()

            #plt.tight_layout()
            #plt.show()
        #slenderness check
        s1=25*wall_thickness
        s2=100*wall_thickness*wall_thickness/effective_depth
        slender=min(s1,s2)
        if(clear_span>slender/1000):
            return("The clear distance from the free end of the cantilever to the lateral restraiant shall not exceeds 25 b or (100 b^2)/d which ever is less. IS:456 Clause 23.3")
            sys.exit()
        # Interactive execution is needed to uncomment and use the following lines:
        point_loads = []
        udl = float(request.form['udl'])
        beam_length = revised_effective_length / 1000
        x, sf, bm, max_sf, max_bm = calculate_sf_bm(point_loads, udl, beam_length)
        #plot_sf_bm(x, sf, bm, max_sf, max_bm)
        ubm = max_bm * 1.5 * -1
        usf = 1.5 * max_sf * -1
        print("ultimate bending moment: ", ubm, "kNm")
        print("ultimate Shear force: ", usf, "kN")
        # -------------------step-3-------------------------------------------
        if (fy == 415):
            mul = .138 * fck * wall_thickness * effective_depth * effective_depth / 1000000
        elif (fy == 250):
            mul = .148 * fck * wall_thickness * effective_depth * effective_depth / 1000000
        elif (fy == 500):
            mul = .133 * fck * wall_thickness * effective_depth * effective_depth / 1000000
        print("Mulimt : ", mul, "kNm")
        if (mul > ubm):
            ultimate_bending_moment = ubm
            b = wall_thickness
            print("The section is Singly Reinforced")
            # ---------------Ast--------------------------------------
            ast = 0.00574712643678161 * (
                    87 * b * effective_depth * fck -
                    9.32737905308882 * (b * fck * (
                    -400 * ultimate_bending_moment * 1000000 + 87 * b * effective_depth ** 2 * fck)) ** 0.5) / fy
            print("ast", ast)
            astmin = 0.85 * b * effective_depth / fy
            print("astmin", astmin)
            astmax = .04 * b * provided_depth
            print("Maximum Ast:", astmax)
            ast=max(ast,astmin)
            if (astmax < astmin or astmax < ast):
                return("Revise Section,Tensile Reinforcement Exceeds 4%")
                sys.exit()
            # --------------------------------------Top bars------------------------
            if (ast > astmin):
                print("Ast will be governing for steel arrangement")
                main_bar = [12, 16, 20, 25, 32, 40]
                results = []
                for num in main_bar:
                    # Calculate the result
                    result = max(ast / (num * num * .785), 2)
                    results.append((num, math.ceil(result)))

                # Find suitable bar and count
                suitable_bars = [(num, count) for num, count in results if 2 <= count < 5]
                if suitable_bars:
                    main_bar, no_of_bars_top = suitable_bars[0]  # Select the first suitable option
                else:
                    main_bar, no_of_bars_top = (0, 0)  # Default to zero if no suitable option is found

                # Calculate the area of steel provided and percentage
                ab = no_of_bars_top * 0.78539816339744830961566084581988 * main_bar ** 2
                pt = 100 * ab / (b * effective_depth)

                # print(main_bar, no_of_bars, pt)
                main_bar_provided = main_bar
                # no_of_bars = round(ast / (0.78539816339744830961566084581988 * main_bar ** 2), 0)
                print("provide", no_of_bars_top, "-Φ", main_bar, " mm as main bars at the top")
                # ab = no_of_bars * 0.78539816339744830961566084581988 * main_bar ** 2
                # pt = 100 * ab / (b * effective_depth)
                print("percentage of steel provided(Tension Reinforcement): ", pt)
            else:
                main_bar = [12, 16, 20, 25, 32, 40]
                results = []
                for num in main_bar:
                    # Calculate the result
                    result = max(astmin / (num * num * .785), 2)
                    results.append((num, math.ceil(result)))

                # Find suitable bar and count
                suitable_bars = [(num, count) for num, count in results if 2 <= count < 5]
                if suitable_bars:
                    main_bar, no_of_bars_top = suitable_bars[0]  # Select the first suitable option
                else:
                    main_bar, no_of_bars_top = (0, 0)  # Default to zero if no suitable option is found

                # Calculate the area of steel provided and percentage
                ab = no_of_bars_top * 0.78539816339744830961566084581988 * main_bar ** 2
                pt = 100 * ab / (b * effective_depth)

                # print(main_bar, no_of_bars, pt)
                main_bar_provided = main_bar
                # no_of_bars = round(ast / (0.78539816339744830961566084581988 * main_bar ** 2), 0)
                print("provide", no_of_bars_top, "-Φ", main_bar, " mm as main bars at the top")
                # ab = no_of_bars * 0.78539816339744830961566084581988 * main_bar ** 2
                # pt = 100 * ab / (b * effective_depth)
                print("percentage of steel provided(Tension Reinforcement): ", pt)
            # -----------------------------------bottom bars---------------------------------------
            bottom_bar = [12, 16, 20, 25, 32, 40]
            results1 = []
            for num in bottom_bar:
                # Calculate the result
                result1 = max(astmin / (num * num * .785), 2)
                results1.append((num, math.ceil(result1)))

            # Find suitable bar and count
            suitable_bars = [(num, count) for num, count in results1 if 2 <= count < 5]
            if suitable_bars:
                bottom_bar, no_of_bars_bottom = suitable_bars[0]  # Select the first suitable option
            else:
                bottom_bar, no_of_bars_bottom = (0, 0)  # Default to zero if no suitable option is found
            if (no_of_bars_bottom == 0):
                no_of_bars_bottom = 2
                bottom_bar = 12

            # Calculate the area of steel provided and percentage
            ab = no_of_bars_bottom * 0.78539816339744830961566084581988 * bottom_bar ** 2
            pt = 100 * ab / (b * effective_depth)

            # print(main_bar, no_of_bars, pt)
            bottom_bar_provided = bottom_bar
            # no_of_bars = round(ast / (0.78539816339744830961566084581988 * main_bar ** 2), 0)
            print("provide", no_of_bars_bottom, "-Φ", bottom_bar, " mm as main bars at the bottom")

            print("percentage of steel provided(Compression Reinforcement): ", pt)
            #side-face
            if provided_depth > 750:
                sideast = 0.0005 * wall_thickness * provided_depth
                side_bar = [12, 16, 20, 25, 32, 40]
                results1 = []
                print(sideast)
                # Calculate the required number of bars for each available diameter
                for num in side_bar:
                    # Calculate the result
                    required_area_per_bar = max(sideast / (num * num * 0.785), 2)
                    # Store the diameter and the required number of bars (rounded up)
                    results1.append((num, math.ceil(required_area_per_bar)))

                # Find suitable bars and count
                suitable_bars = [(num, count) for num, count in results1 if 1 <= count < 5]
                if suitable_bars:
                    side_bar, no_of_bars_side = suitable_bars[0]  # Select the first suitable option
                else:
                    side_bar, no_of_bars_side = (12, 1)  # Default to 12mm bar and 1 bar if no suitable option is found

                # Print the result
                print("Provide", no_of_bars_side, "no of", side_bar, "mm bars on each side of the beam")

            # --------------------------check for shear-----------------------------
            ultimate_shear_force = usf
            vu = ultimate_shear_force * 1000
            tv = vu / (b * effective_depth)
            print(effective_depth)
            p = 100 * ast / (b * effective_depth)
            # print(p)

            beta = 0.8 * fck / (6.89 * p)
            f = (0.8 * fck) ** 0.5
            brta = ((1 + 5 * beta) ** 0.5) - 1
            tc = 0.85 * f * brta / (6 * beta)
            # tc=(0.85*((0.8*fck)**0.5)*((1+5*beta)**0.5)-1)/(6*beta)
            print("tc value: ", tc)
            print("tv value: ", tv)
            if (tv > tc and tv <= tcmax):
                Vus = ultimate_shear_force * 1000 - (tc * b * effective_depth)
                print("Vus value: ", Vus)
                stdia = 8
                leg = 2

                sv = 0.87 * fy * effective_depth * leg * 0.78539816339744830961566084581988 * stdia ** 2 / Vus
                print(sv)
                spacing = min(0.75 * effective_depth, 300)
                max_spacing = (spacing // 25) * 25
                # print(max_spacing)
                print("Provide Φ", stdia, "- mm ", leg, "vertical stirrups @", max_spacing, "c/c")
            elif (tv <= tc):
                stdia = 8
                leg = 2

                sv = 0.87 * fy * leg * 0.78539816339744830961566084581988 * stdia ** 2 / (0.4 * wall_thickness)
                spacing = min(0.75 * effective_depth, 300)
                max_spacing = (spacing // 25) * 25
                # print(max_spacing)
                print("Provide Φ", stdia, "- mm ", leg, "vertical stirrups @", max_spacing, "c/c")
            else:
                return("revise section (per Cl. 40.2.3, IS 456: 2000, pp. 72")
            # step 6:Check for Deflection
            l = revised_effective_length
            Actualspan = l / effective_depth
            bd = b * effective_depth / (100 * ast)
            fs = 0.58 * fy * ast / (no_of_bars_top * 0.78539816339744830961566084581988 * main_bar ** 2)

            mf = 1 / (0.225 + 0.003228 * fs - 0.625 * math.log10(bd))
            allowablespan = 7 * mf
            print("modification factor: ", mf)
            # -----------development length-------------
            phi = main_bar
            print(main_bar)
            print(bottom_bar)
            tss = 0.87 * fy
            if (fck == 20):
                tbd = 1.2 * 1.6
            elif (fck == 25):
                tbd = 1.4 * 2.24
            elif (fck == 30):
                tbd = 1.5 * 2.4
            elif (fck == 35):
                tbd = 1.7 * 2.72
            elif (fck >= 40):
                tbd = 1.9 * 3.04
            ld = phi * tss / (4 * tbd)
            print(ld)
            # ---------------shear reinforcement--------------------
            as1 = 0.1 * wall_thickness * effective_depth / 100
            no_of_bars_shear_face = math.ceil((as1 / 2) / (0.785 * 144))
            spacing_of_bars = provided_depth - nominal_cover * 2 - stdia * 2 - main_bar / 2 - bottom_bar_provided / 2
            no_of_bars_shear = math.ceil((spacing_of_bars / wall_thickness) - 1)
            print(no_of_bars_shear)
            if (allowablespan > Actualspan):
                print(" The section is safe under deflection")
            else:
                return(" revise section")
            no_bars_top = no_of_bars_top
            main_bar = main_bar
            top_bar = main_bar
            effective_cover = ed1 - ed
            stdia = stdia
            clear_span = clear_span / 100
            wall_thickness = wall_thickness / 100
            overall_depth = provided_depth / 100
            revised_effective_length = beam_length / 100
            cd = cd / 100
            # print(clear_span)
            # Initiate DXF file and access model space
            doc = ezdxf.new(setup=True)
            msp = doc.modelspace()
            dimstyle = doc.dimstyles.new("MyCustomStyle")
            dimstyle.dxf.dimasz = 0.5
            dimstyle.dxf.dimtxt = .1
            # dimstyle.dxf.dim
            # which is a shortcut (including validation) for
            doc.header['$INSUNITS'] = units.MM

            x = -cd + nominal_cover / 100
            y = overall_depth - nominal_cover / 100
            x1 = clear_span * 1000 - nominal_cover / 100
            x11 = clear_span * 100
            y1 = overall_depth - nominal_cover / 100
            x3 = -cd + nominal_cover / 100
            x31 = clear_span * 800
            y3 = nominal_cover / 100
            x4 = clear_span * 1000 + - nominal_cover / 100
            y4 = nominal_cover / 100
            x5 = -wall_thickness / 2
            y5 = overall_depth / 1.2
            x6 = clear_span * 1000 + 2 * wall_thickness / 4
            y6 = overall_depth / 1.2

            # Create a Line
            msp.add_line((x, y), (x1, y1))  # top bar
            msp.add_line((x, y), (x, -ld / 100))
            msp.add_line((x3, y3), (x4, y4))  # bottom bar
            msp.add_line((0, 0), (clear_span * 1000, 0))
            msp.add_line((0, 0), (-cd, 0))
            msp.add_line((-cd, 0), (-cd, overall_depth))
            msp.add_line((-cd, overall_depth), (0, overall_depth))
            msp.add_line((-cd, 0), (-cd, -overall_depth))
            msp.add_line((-cd, -overall_depth), (0, -overall_depth))
            msp.add_line((-cd, overall_depth), (-cd, 2 * overall_depth))  # ------uppper wall
            msp.add_line((-cd, 2 * overall_depth), (0, 2 * overall_depth))
            msp.add_line((0, 2 * overall_depth), (0, overall_depth))  # ------upper wall
            msp.add_line((0, -overall_depth), (0, 0))
            # msp.add_line((0,0),(0,overall_depth))
            msp.add_line((0, overall_depth), (clear_span * 1000, overall_depth))
            msp.add_line((clear_span * 1000, overall_depth), (clear_span * 1000, 0))
            # msp.add_line((clear_span * 1000, 0), (clear_span * 1000, -overall_depth))
            # msp.add_line((clear_span * 1000, -overall_depth), (clear_span * 1000 + wall_thickness, -overall_depth))
            # msp.add_line((clear_span * 1000 + wall_thickness, -overall_depth),(clear_span * 1000 + wall_thickness, overall_depth))
            msp.add_line((clear_span * 500, 0), (clear_span * 500, overall_depth))
            # cross-section
            msp.add_line((0, -5 * overall_depth), (wall_thickness, -5 * overall_depth))  # bottom line
            msp.add_line((0, -5 * overall_depth), (0, -4 * overall_depth))  # left line
            msp.add_line((0, -4 * overall_depth), (wall_thickness, -4 * overall_depth))
            msp.add_line((wall_thickness, -4 * overall_depth), (wall_thickness, -5 * overall_depth))
            # --stirrup cross
            nominal_cover = nominal_cover / 100
            msp.add_line((0 + nominal_cover, -5 * overall_depth + nominal_cover),
                         (wall_thickness - nominal_cover, -5 * overall_depth + nominal_cover))  # bottom line
            msp.add_line((0 + nominal_cover, -5 * overall_depth + nominal_cover),
                         (0 + nominal_cover, -4 * overall_depth - nominal_cover))  # left line
            msp.add_line((0 + nominal_cover, -4 * overall_depth - nominal_cover),
                         (wall_thickness - nominal_cover, -4 * overall_depth - nominal_cover))
            msp.add_line((wall_thickness - nominal_cover, -4 * overall_depth - nominal_cover),
                         (wall_thickness - nominal_cover, -5 * overall_depth + nominal_cover))
            ml_builder = msp.add_multileader_mtext("Standard")

            ct = "Provide", no_of_bars_bottom, "Φ", main_bar, "- mm as \n main bars at the bottom"
            content_str = ', '.join(map(str, ct))
            ml_builder.set_content(content_str, style="OpenSans", char_height=.7,
                                   alignment=mleader.TextAlignment.center, )

            X22 = clear_span * 900
            X11 = clear_span * 50
            ml_builder.add_leader_line(mleader.ConnectionSide.left, [Vec2(X11, y4)])
            ml_builder.add_leader_line(mleader.ConnectionSide.right, [Vec2(X22, y4)])
            ml_builder.build(insert=Vec2(clear_span * 500, -1 * overall_depth))

            # -----top bar
            ml_builder1 = msp.add_multileader_mtext("Standard")
            content_str1 = "Provide", no_of_bars_top, "-Φ", top_bar, "- mm \n as main bars at the top"
            content_str1 = ', '.join(map(str, content_str1))
            ml_builder1.set_content(content_str1, style="OpenSans", char_height=.7,
                                    alignment=mleader.TextAlignment.center, )
            X32 = clear_span * 50
            X31 = clear_span * 900
            ml_builder1.add_leader_line(mleader.ConnectionSide.right, [Vec2(X31, y1)])
            ml_builder1.add_leader_line(mleader.ConnectionSide.left, [Vec2(X32, y1)])
            ml_builder1.build(insert=Vec2(500 * clear_span, 1.5 * overall_depth))
            # ----striupp
            ml_builder2 = msp.add_multileader_mtext("Standard")
            content_str3 = "Provide Φ", stdia, " -mm", leg, "\n" " legged vertical stirrups @", max_spacing, "c/c"
            content_str3 = ', '.join(map(str, content_str3))
            ml_builder2.set_content(
                content_str3,
                style="OpenSans",
                char_height=1,
                alignment=mleader.TextAlignment.left,  # set MTEXT alignment!
            )
            X6 = clear_span * 1000
            Y6 = overall_depth
            ml_builder2.add_leader_line(mleader.ConnectionSide.left, [Vec2(X6 / 2, Y6 / 2)])
            ml_builder2.build(insert=Vec2(clear_span * 800, 2 * overall_depth))
            # dimensions
            # Adda horizontal linear DIMENSION entity:
            dimstyle = doc.dimstyles.get("EZDXF")
            dimstyle.dxf.dimtxt = 1
            dim = msp.add_linear_dim(
                base=(0, -2 * overall_depth),  # location of the dimension line
                p1=(0, 0),  # 1st measurement point
                p2=(clear_span * 1000, 0),  # 2nd measurement point
                dimstyle="EZDXF",  # default dimension style
            )
            dim1 = msp.add_linear_dim(
                base=(0, -2 * overall_depth),  # location of the dimension line
                p1=(-cd, -overall_depth),  # 1st measurement point
                p2=(0, -overall_depth),  # 2nd measurement point
                dimstyle="EZDXF",  # default dimension style
            )
            '''dim2 = msp.add_linear_dim(
                base=(0, -2 * overall_depth),  # location of the dimension line
                p1=(clear_span * 1000, 0),  # 1st measurement point
                p2=(clear_span * 1000 + wall_thickness, 0),  # 2nd measurement point
                dimstyle="EZDXF",  # default dimension style
            )'''
            # hatch
            hatch = msp.add_hatch()
            hatch.set_pattern_fill("ANSI32", scale=.1)
            hatch.paths.add_polyline_path(
                [(0, 0), (-cd, 0), (-cd, -overall_depth), (0, -overall_depth)], is_closed=True
            )
            hatch1 = msp.add_hatch()
            hatch1.set_pattern_fill("ANSI32", scale=.1)
            hatch1.paths.add_polyline_path(
                [(-cd, overall_depth), (-cd, 2 * overall_depth),
                 (0, 2 * overall_depth), (0, overall_depth)], is_closed=True
            )

            def create_dots(dot_centers, dot_radius, top):
                # Create a new DXF document

                # Create solid dots at specified centers with given radius
                for center in dot_centers:
                    # Create a HATCH entity with a solid fill
                    hatch = msp.add_hatch()
                    # Add a circular path to the hatch as its boundary
                    edge_path = hatch.paths.add_edge_path()
                    edge_path.add_arc(center=center, radius=dot_radius, start_angle=0, end_angle=360)
                    # Set the hatch pattern to solid
                    hatch.set_solid_fill()
                    if (top == 1):
                        msp.add_diameter_dim(
                            center=center,
                            radius=dot_radius,
                            # text=None,
                            dimstyle="EZ_RADIUS",
                            angle=135,  # Adjust the angle as needed
                            override={'dimtad': 0, 'dimasz': .2, 'dimexo': 5000, "dimtoh": 1, "dimlfac": 100},
                            # 16MM # Moves dimension line outside if it overlaps with the circle
                            dxfattribs={'layer': 'dimensions'}
                        ).render()
                    else:
                        msp.add_diameter_dim(
                            center=center,
                            radius=dot_radius,
                            dimstyle="EZ_RADIUS",
                            angle=135,  # Adjust the angle as needed
                            override={'dimtad': 0, 'dimasz': .2, 'dimexo': 5000, "dimtoh": 1, "dimlfac": 100},
                            # 12MM  # Moves dimension line outside if it overlaps with the circle
                            dxfattribs={'layer': 'dimensions'}
                        ).render()

                # Create a rectangle from the provided corners
                # Assuming rectangle_corners is a list of tuples [(x1, y1), (x2, y2), (x3, y3), (x4, y4)] in consecutive order
                # Save the document

            # Exam

            if (no_bars_top == 3):
                cx1 = (0 + nominal_cover + top_bar / 200)
                cx2 = ((0 + nominal_cover + top_bar / 200 + 0 + wall_thickness - nominal_cover - top_bar / 200)) / 2
                cx3 = (0 + wall_thickness - nominal_cover - top_bar / 200)
                cy1 = -4 * overall_depth - nominal_cover - top_bar / 200
                dot_centers = [(cx1, cy1), (cx2, cy1), (cx3, cy1)]  # Replace with the actual centers of the dots
                dot_radius = top_bar / 200
                top = 1
                create_dots(dot_centers, dot_radius, top)

            elif (no_bars_top == 2):
                cx1 = (0 + nominal_cover + top_bar / 200)
                cx3 = (0 + wall_thickness - nominal_cover - top_bar / 200)
                cy1 = -4 * overall_depth - nominal_cover - top_bar / 200
                dot_centers = [(cx1, cy1), (cx3, cy1)]  # Replace with the actual centers of the dots
                dot_radius = top_bar / 200
                top = 1
                create_dots(dot_centers, dot_radius, top)

            elif (no_bars_top == 4):
                cx1 = (0 + nominal_cover + top_bar / 200)
                cx2 = (wall_thickness - nominal_cover * 2) / 3 + nominal_cover
                cx3 = 2 * (wall_thickness - nominal_cover * 2) / 3 + nominal_cover
                cx4 = (0 + wall_thickness - nominal_cover - top_bar / 200)
                cy1 = -4 * overall_depth - nominal_cover - top_bar / 200
                dot_centers = [(cx1, cy1), (cx2, cy1), (cx3, cy1),
                               (cx4, cy1)]  # Replace with the actual centers of the dots
                dot_radius = top_bar / 200
                top = 1
                create_dots(dot_centers, dot_radius, top)

            else:
                print("bars cannot be arranged")

            if (no_of_bars_bottom == 3):  # --------------------------------------------bottom
                x1 = (0 + nominal_cover + main_bar / 200)
                x2 = ((0 + nominal_cover + main_bar / 200 + 0 + wall_thickness - nominal_cover - main_bar / 200)) / 2
                x3 = (0 + wall_thickness - nominal_cover - main_bar / 200)
                y2 = -5 * overall_depth + nominal_cover + main_bar / 200
                dot_centers1 = [(x1, y2), (x2, y2), (x3, y2)]  # Replace with the actual centers of the dots
                dot_radius1 = main_bar / 200
                bottom = 10
                create_dots(dot_centers1, dot_radius1, bottom)
            elif (no_of_bars_bottom == 2):
                x1 = (0 + nominal_cover + main_bar / 200)
                x3 = (0 + wall_thickness - nominal_cover - main_bar / 200)
                y2 = -5 * overall_depth + nominal_cover + main_bar / 200
                dot_centers1 = [(x1, y2), (x3, y2)]  # Replace with the actual centers of the dots
                dot_radius1 = main_bar / 200
                bottom = 10
                create_dots(dot_centers1, dot_radius1, bottom)
            elif (no_of_bars_bottom == 4):
                x1 = (0 + nominal_cover + main_bar / 200)
                x2 = (wall_thickness - nominal_cover * 2) / 3 + nominal_cover
                x3 = 2 * (wall_thickness - nominal_cover * 2) / 3 + nominal_cover
                x4 = (0 + wall_thickness - nominal_cover - main_bar / 200)
                y2 = -5 * overall_depth + nominal_cover + main_bar / 200
                dot_centers1 = [(x1, y2), (x2, y2), (x3, y2), (x4, y2)]  # Replace with the actual centers of the dots
                dot_radius1 = main_bar / 200
                bottom = 10
                create_dots(dot_centers1, dot_radius1, bottom)
            else:
                print("bars cannot be arranged")

            # cross section dimension
            dim3 = msp.add_linear_dim(
                base=(0, -5.5 * overall_depth),  # location of the dimension line
                p1=(0, -4 * overall_depth),  # 1st measurement point
                p2=(wall_thickness, -4 * overall_depth),  # 2nd measurement point
                dimstyle="EZDXF",  # default dimension style
            )
            msp.add_linear_dim(base=(-1 * wall_thickness, -3.5 * overall_depth), p1=(0, -4 * overall_depth),
                               p2=(0, -5 * overall_depth), angle=90).render()  # cross section
            # msp.add_linear_dim(base=(1.1*clear_span*1000, overall_depth/2), p1=(1.2*clear_span*1000, 0), p2=(1.2*clear_span*1000, overall_depth), angle=90).render()
            msp.add_linear_dim(base=(-2 * cd, overall_depth / 2), p1=(-cd, 0),
                               p2=(-cd, overall_depth), angle=90).render()  # overall depth dim

            text_string = "LONGITUDINAL SECTION (all units are in mm)"
            insert_point = (100 * clear_span, -3 * overall_depth)  # X, Y coordinates where the text will be inserted.
            text_height = 1  # Height of the text.

            # Add text to the modelspace.
            msp.add_text(
                text_string,
                dxfattribs={
                    'insert': insert_point,
                    'height': text_height,
                    # Additional attributes such as font, rotation, and color can be specified here.
                    'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                    'rotation': 0,
                    'color': 7
                }
            )

            text_string = "SECTION A-A"
            insert_point = (-wall_thickness, -7 * overall_depth)  # X, Y coordinates where the text will be inserted.
            text_height = 1
            # Add text to the modelspace.
            msp.add_text(
                text_string,
                dxfattribs={
                    'insert': insert_point,
                    'height': text_height,
                    # Additional attributes such as font, rotation, and color can be specified here.
                    'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                    'rotation': 0,
                    'color': 7
                }
            )
            text_string = "SECTION B-B"
            insert_point = (400 * clear_span, -7 * overall_depth)  # X, Y coordinates where the text will be inserted.
            text_height = 1
            # Add text to the modelspace.
            msp.add_text(
                text_string,
                dxfattribs={
                    'insert': insert_point,
                    'height': text_height,
                    # Additional attributes such as font, rotation, and color can be specified here.
                    'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                    'rotation': 0,
                    'color': 7
                }
            )
            # section b-b
            msp.add_line((500 * clear_span, -5 * overall_depth),
                         (500 * clear_span - wall_thickness, -5 * overall_depth))  # bottom line
            msp.add_line((500 * clear_span - wall_thickness, -5 * overall_depth),
                         (500 * clear_span - wall_thickness, -4 * overall_depth))  # left line
            msp.add_line((500 * clear_span - wall_thickness, -4 * overall_depth),
                         (500 * clear_span, -4 * overall_depth))
            msp.add_line((500 * clear_span, -4 * overall_depth), (500 * clear_span, -5 * overall_depth))
            # --stirrup cross
            nominal_cover = nominal_cover
            msp.add_line((500 * clear_span - nominal_cover, -5 * overall_depth + nominal_cover),
                         (500 * clear_span - wall_thickness + nominal_cover,
                          -5 * overall_depth + nominal_cover))  # bottom line
            msp.add_line((500 * clear_span - wall_thickness + nominal_cover, -5 * overall_depth + nominal_cover),
                         (500 * clear_span - wall_thickness + nominal_cover,
                          -4 * overall_depth - nominal_cover))  # left line
            msp.add_line((500 * clear_span - wall_thickness + nominal_cover, -4 * overall_depth - nominal_cover),
                         (500 * clear_span - nominal_cover, -4 * overall_depth - nominal_cover))
            msp.add_line((500 * clear_span - nominal_cover, -4 * overall_depth - nominal_cover),
                         (500 * clear_span - nominal_cover, -5 * overall_depth + nominal_cover))

            # cross section dimension
            dim3 = msp.add_linear_dim(
                base=(400 * clear_span, -5.5 * overall_depth),  # location of the dimension line
                p1=(500 * clear_span, -5 * overall_depth),  # 1st measurement point
                p2=(500 * clear_span - wall_thickness, -5 * overall_depth),  # 2nd measurement point
                dimstyle="EZDXF",  # default dimension style
            )
            msp.add_linear_dim(base=(300 * clear_span, -3.5 * overall_depth),
                               p1=(500 * clear_span - wall_thickness, -5 * overall_depth),
                               p2=(500 * clear_span - wall_thickness, -4 * overall_depth),
                               angle=90).render()  # cross section

            def create_dots_bb(dot_centers, dot_radius, top):
                # Create solid dots at specified centers with given radius
                for center in dot_centers:
                    # Create a HATCH entity with a solid fill
                    hatch = msp.add_hatch()
                    # Add a circular path to the hatch as its boundary
                    edge_path = hatch.paths.add_edge_path()
                    edge_path.add_arc(center=center, radius=dot_radius, start_angle=0, end_angle=360)
                    # Set the hatch pattern to solid
                    hatch.set_solid_fill()
                    if (top == 1):
                        msp.add_diameter_dim(
                            center=center,
                            radius=dot_radius,
                            # text=None,
                            dimstyle="EZ_RADIUS",
                            angle=135,  # Adjust the angle as needed
                            override={'dimtad': 0, 'dimasz': .2, 'dimexo': 5000, "dimtoh": 1, "dimlfac": 100},
                            # 16MM # Moves dimension line outside if it overlaps with the circle
                            dxfattribs={'layer': 'dimensions'}
                        ).render()
                    else:
                        msp.add_diameter_dim(
                            center=center,
                            radius=dot_radius,
                            dimstyle="EZ_RADIUS",
                            angle=135,  # Adjust the angle as needed
                            override={'dimtad': 0, 'dimasz': .2, 'dimexo': 5000, "dimtoh": 1, "dimlfac": 100},
                            # 12MM  # Moves dimension line outside if it overlaps with the circle
                            dxfattribs={'layer': 'dimensions'}
                        ).render()

                # Create a rectangle from the provided corners
                # Assuming rectangle_corners is a list of tuples [(x1, y1), (x2, y2), (x3, y3), (x4, y4)] in consecutive order
                # Save the document

            # Exam

            if (no_bars_top == 3):
                cx1 = (500 * clear_span - wall_thickness + nominal_cover + top_bar / 200)
                cx2 = ((
                        500 * clear_span - wall_thickness + nominal_cover + top_bar / 200 + 500 * clear_span - nominal_cover - top_bar / 200)) / 2
                cx3 = (500 * clear_span - nominal_cover - top_bar / 200)
                cy1 = -4 * overall_depth - nominal_cover - top_bar / 200
                dot_centers = [(cx1, cy1), (cx2, cy1), (cx3, cy1)]  # Replace with the actual centers of the dots
                dot_radius = top_bar / 200
                top = 1
                create_dots_bb(dot_centers, dot_radius, top)

            elif (no_bars_top == 2):
                cx1 = (500 * clear_span - wall_thickness + nominal_cover + top_bar / 200)
                cx3 = (500 * clear_span - nominal_cover - top_bar / 200)
                cy1 = -4 * overall_depth - nominal_cover - top_bar / 200
                dot_centers = [(cx1, cy1), (cx3, cy1)]  # Replace with the actual centers of the dots
                dot_radius = top_bar / 200
                top = 1
                create_dots_bb(dot_centers, dot_radius, top)

            elif (no_bars_top == 4):
                cx1 = (500 * clear_span - wall_thickness + nominal_cover + top_bar / 200)
                cx2 = (500 * clear_span - wall_thickness + wall_thickness / 3 + top_bar / 100)
                cx3 = (500 * clear_span - wall_thickness + 2 * wall_thickness / 3 - top_bar / 100)
                cx4 = (500 * clear_span - nominal_cover - top_bar / 200)
                cy1 = -4 * overall_depth - nominal_cover - top_bar / 200
                dot_centers = [(cx1, cy1), (cx2, cy1), (cx3, cy1),
                               (cx4, cy1)]  # Replace with the actual centers of the dots
                dot_radius = top_bar / 200
                top = 1
                create_dots_bb(dot_centers, dot_radius, top)

            else:
                print("bars cannot be arranged")

            if (no_of_bars_bottom == 3):  # --------------------------------------------bottom
                x1 = (500 * clear_span - wall_thickness + nominal_cover + main_bar / 200)
                x2 = ((
                        500 * clear_span - wall_thickness + nominal_cover + main_bar / 200 + 500 * clear_span - nominal_cover - main_bar / 200)) / 2
                x3 = (500 * clear_span - nominal_cover - main_bar / 200)
                y2 = -5 * overall_depth + nominal_cover + main_bar / 200
                dot_centers1 = [(x1, y2), (x2, y2), (x3, y2)]  # Replace with the actual centers of the dots
                dot_radius1 = main_bar / 200
                bottom = 10
                create_dots_bb(dot_centers1, dot_radius1, bottom)
            elif (no_of_bars_bottom == 2):
                x1 = (500 * clear_span - wall_thickness + nominal_cover + main_bar / 200)
                x3 = (500 * clear_span - nominal_cover - main_bar / 200)
                y2 = -5 * overall_depth + nominal_cover + main_bar / 200
                dot_centers1 = [(x1, y2), (x3, y2)]  # Replace with the actual centers of the dots
                dot_radius1 = main_bar / 200
                bottom = 10
                create_dots_bb(dot_centers1, dot_radius1, bottom)
            elif (no_of_bars_bottom == 4):
                x1 = (500 * clear_span - wall_thickness + nominal_cover + main_bar / 200)
                x2 = (500 * clear_span - wall_thickness + wall_thickness / 3) + main_bar / 200
                x3 = (500 * clear_span - wall_thickness + 2 * wall_thickness / 3) - main_bar / 200
                x4 = (500 * clear_span - nominal_cover - main_bar / 200)
                y2 = -5 * overall_depth + nominal_cover + main_bar / 200
                dot_centers1 = [(x1, y2), (x2, y2), (x3, y2), (x4, y2)]  # Replace with the actual centers of the dots
                dot_radius1 = main_bar / 200
                bottom = 10
                create_dots_bb(dot_centers1, dot_radius1, bottom)
            else:
                print("bars cannot be arranged")
            text_string = "SECTION C-C"
            insert_point = (1000 * clear_span, -7 * overall_depth)  # X, Y coordinates where the text will be inserted.
            text_height = 1
            # Add text to the modelspace.
            msp.add_text(
                text_string,
                dxfattribs={
                    'insert': insert_point,
                    'height': text_height,
                    # Additional attributes such as font, rotation, and color can be specified here.
                    'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                    'rotation': 0,
                    'color': 7
                }
            )
            # section b-b
            msp.add_line((1000 * clear_span, -5 * overall_depth),
                         (1000 * clear_span - wall_thickness, -5 * overall_depth))  # bottom line
            msp.add_line((1000 * clear_span - wall_thickness, -5 * overall_depth),
                         (1000 * clear_span - wall_thickness, -4 * overall_depth))  # left line
            msp.add_line((1000 * clear_span - wall_thickness, -4 * overall_depth),
                         (1000 * clear_span, -4 * overall_depth))
            msp.add_line((1000 * clear_span, -4 * overall_depth), (1000 * clear_span, -5 * overall_depth))
            # --stirrup cross
            nominal_cover = nominal_cover
            msp.add_line((1000 * clear_span - nominal_cover, -5 * overall_depth + nominal_cover),
                         (1000 * clear_span - wall_thickness + nominal_cover,
                          -5 * overall_depth + nominal_cover))  # bottom line
            msp.add_line((1000 * clear_span - wall_thickness + nominal_cover, -5 * overall_depth + nominal_cover),
                         (
                             1000 * clear_span - wall_thickness + nominal_cover,
                             -4 * overall_depth - nominal_cover))  # left line
            msp.add_line((1000 * clear_span - wall_thickness + nominal_cover, -4 * overall_depth - nominal_cover),
                         (1000 * clear_span - nominal_cover, -4 * overall_depth - nominal_cover))
            msp.add_line((1000 * clear_span - nominal_cover, -4 * overall_depth - nominal_cover),
                         (1000 * clear_span - nominal_cover, -5 * overall_depth + nominal_cover))

            # cross section dimension
            dim3 = msp.add_linear_dim(
                base=(900 * clear_span, -5.5 * overall_depth),  # location of the dimension line
                p1=(1000 * clear_span, -5 * overall_depth),  # 1st measurement point
                p2=(1000 * clear_span - wall_thickness, -5 * overall_depth),  # 2nd measurement point
                dimstyle="EZDXF",  # default dimension style
            )
            msp.add_linear_dim(base=(900 * clear_span, -3.5 * overall_depth),
                               p1=(1000 * clear_span - wall_thickness, -5 * overall_depth),
                               p2=(1000 * clear_span - wall_thickness, -4 * overall_depth),
                               angle=90).render()  # cross section

            def create_dots_cc(dot_centers, dot_radius, top):
                # Create solid dots at specified centers with given radius
                for center in dot_centers:
                    # Create a HATCH entity with a solid fill
                    hatch = msp.add_hatch()
                    # Add a circular path to the hatch as its boundary
                    edge_path = hatch.paths.add_edge_path()
                    edge_path.add_arc(center=center, radius=dot_radius, start_angle=0, end_angle=360)
                    # Set the hatch pattern to solid
                    hatch.set_solid_fill()
                    if (top == 1):
                        msp.add_diameter_dim(
                            center=center,
                            radius=dot_radius,
                            # text=None,
                            dimstyle="EZ_RADIUS",
                            angle=135,  # Adjust the angle as needed
                            override={'dimtad': 0, 'dimasz': .2, 'dimexo': 5000, "dimtoh": 1, "dimlfac": 100},
                            # 16MM # Moves dimension line outside if it overlaps with the circle
                            dxfattribs={'layer': 'dimensions'}
                        ).render()
                    else:
                        msp.add_diameter_dim(
                            center=center,
                            radius=dot_radius,
                            dimstyle="EZ_RADIUS",
                            angle=135,  # Adjust the angle as needed
                            override={'dimtad': 0, 'dimasz': .2, 'dimexo': 5000, "dimtoh": 1, "dimlfac": 100},
                            # 12MM  # Moves dimension line outside if it overlaps with the circle
                            dxfattribs={'layer': 'dimensions'}
                        ).render()

                # Create a rectangle from the provided corners
                # Assuming rectangle_corners is a list of tuples [(x1, y1), (x2, y2), (x3, y3), (x4, y4)] in consecutive order
                # Save the document

            # Exam

            if (no_bars_top == 3):
                cx1 = (1000 * clear_span - wall_thickness + nominal_cover + top_bar / 200)
                cx2 = ((
                        1000 * clear_span - wall_thickness + nominal_cover + top_bar / 200 + 1000 * clear_span - nominal_cover - top_bar / 200)) / 2
                cx3 = (1000 * clear_span - nominal_cover - top_bar / 200)
                cy1 = -4 * overall_depth - nominal_cover - top_bar / 200
                dot_centers = [(cx1, cy1), (cx2, cy1), (cx3, cy1)]  # Replace with the actual centers of the dots
                dot_radius = top_bar / 200
                top = 1
                create_dots_bb(dot_centers, dot_radius, top)

            elif (no_bars_top == 2):
                cx1 = (1000 * clear_span - wall_thickness + nominal_cover + top_bar / 200)
                cx3 = (1000 * clear_span - nominal_cover - top_bar / 200)
                cy1 = -4 * overall_depth - nominal_cover - top_bar / 200
                dot_centers = [(cx1, cy1), (cx3, cy1)]  # Replace with the actual centers of the dots
                dot_radius = top_bar / 200
                top = 1
                create_dots_bb(dot_centers, dot_radius, top)

            elif (no_bars_top == 4):
                cx1 = (1000 * clear_span - wall_thickness + nominal_cover + top_bar / 200)
                cx2 = (1000 * clear_span - wall_thickness + wall_thickness / 3 + top_bar / 200)
                cx3 = (1000 * clear_span - wall_thickness + 2 * wall_thickness / 3 - top_bar / 200)
                cx4 = (1000 * clear_span - nominal_cover - top_bar / 200)
                cy1 = -4 * overall_depth - nominal_cover - top_bar / 200
                dot_centers = [(cx1, cy1), (cx2, cy1), (cx3, cy1),
                               (cx4, cy1)]  # Replace with the actual centers of the dots
                dot_radius = top_bar / 200
                top = 1
                create_dots_bb(dot_centers, dot_radius, top)

            else:
                print("bars cannot be arranged")

            if (no_of_bars_bottom == 3):  # --------------------------------------------bottom
                x1 = (1000 * clear_span - wall_thickness + nominal_cover + main_bar / 200)
                x2 = ((
                        1000 * clear_span - wall_thickness + nominal_cover + main_bar / 200 + 1000 * clear_span - nominal_cover - main_bar / 200)) / 2
                x3 = (1000 * clear_span - nominal_cover - main_bar / 200)
                y2 = -5 * overall_depth + nominal_cover + main_bar / 200
                dot_centers1 = [(x1, y2), (x2, y2), (x3, y2)]  # Replace with the actual centers of the dots
                dot_radius1 = main_bar / 200
                bottom = 10
                create_dots_bb(dot_centers1, dot_radius1, bottom)
            elif (no_of_bars_bottom == 2):
                x1 = (1000 * clear_span - wall_thickness + nominal_cover + main_bar / 200)
                x3 = (1000 * clear_span - nominal_cover - main_bar / 200)
                y2 = -5 * overall_depth + nominal_cover + main_bar / 200
                dot_centers1 = [(x1, y2), (x3, y2)]  # Replace with the actual centers of the dots
                dot_radius1 = main_bar / 200
                bottom = 10
                create_dots_cc(dot_centers1, dot_radius1, bottom)
            elif (no_of_bars_bottom == 4):
                x1 = (1000 * clear_span - wall_thickness + nominal_cover + main_bar / 200)
                x2 = (1000 * clear_span - wall_thickness + wall_thickness / 3) + main_bar / 200
                x3 = (1000 * clear_span - wall_thickness + 2 * wall_thickness / 3) - main_bar / 200
                x4 = (1000 * clear_span - nominal_cover - main_bar / 200)
                y2 = -5 * overall_depth + nominal_cover + main_bar / 200
                dot_centers1 = [(x1, y2), (x2, y2), (x3, y2), (x4, y2)]  # Replace with the actual centers of the dots
                dot_radius1 = main_bar / 200
                bottom = 10
                create_dots_cc(dot_centers1, dot_radius1, bottom)
            else:
                print("bars cannot be arranged")
            if provided_depth > 750:
                sideast = 0.0005 * wall_thickness *  provided_depth
                side_bar = [12, 16, 20, 25, 32, 40]
                results1 = []
                print(sideast)
                # Calculate the required number of bars for each available diameter
                for num in side_bar:
                    # Calculate the result
                    required_area_per_bar = max(sideast / (num * num * 0.785), 2)
                    # Store the diameter and the required number of bars (rounded up)
                    results1.append((num, math.ceil(required_area_per_bar)))

                # Find suitable bars and count
                suitable_bars = [(num, count) for num, count in results1 if 1 <= count < 5]
                if suitable_bars:
                    side_bar, no_of_bars_side = suitable_bars[0]  # Select the first suitable option
                else:
                    side_bar, no_of_bars_side = (12, 1)  # Default to 12mm bar and 1 bar if no suitable option is found

                # Print the result
                print("Provide", no_of_bars_side, "no of", side_bar, "mm bars on each side of the beam")
            temp1 = overall_depth / 3
            if (overall_depth >= 7.5):
                if (temp1 > no_of_bars_side):
                    if (no_of_bars_side == 2):
                        sx = -7.50+ nominal_cover
                        sy = (overall_depth * 2 / 3 - nominal_cover)
                        sx1 = clear_span * 1000  - nominal_cover
                        sx3 = -7.50 + nominal_cover
                        sy3 = nominal_cover + overall_depth / 3
                        sx4 = clear_span * 1000  - nominal_cover
                        msp.add_line((sx, sy), (sx1, sy))  # top side bar
                        msp.add_line((sx3, sy3), (sx4, sy3))  # bottom side bar

                    elif (no_of_bars_side == 3):
                        print(no_of_bars_side)
                        sx = -7.50+ nominal_cover
                        sy = (overall_depth * .5 + nominal_cover)
                        sx1 = clear_span * 1000  - nominal_cover
                        sx3 = -7.50 + nominal_cover
                        sy3 = nominal_cover + overall_depth * .25
                        sx4 = clear_span * 1000 - nominal_cover
                        sy5 = nominal_cover + overall_depth * .75
                        sx5 = clear_span * 1000 - nominal_cover
                        msp.add_line((sx, sy), (sx1, sy))  # top side bar
                        msp.add_line((sx3, sy3), (sx4, sy3))
                        msp.add_line((sx3, sy5), (sx5, sy5))  # bottom side bar

                    def create_dots_bb(dot_centers, dot_radius, top):
                        # Create solid dots at specified centers with given radius
                        for center in dot_centers:
                            # Create a HATCH entity with a solid fill
                            hatch = msp.add_hatch()
                            # Add a circular path to the hatch as its boundary
                            edge_path = hatch.paths.add_edge_path()
                            edge_path.add_arc(center=center, radius=dot_radius, start_angle=0, end_angle=360)
                            # Set the hatch pattern to solid
                            hatch.set_solid_fill()
                            if (top == 1):
                                msp.add_diameter_dim(
                                    center=center,
                                    radius=dot_radius,
                                    # text=None,
                                    dimstyle="EZ_RADIUS",
                                    angle=135,  # Adjust the angle as needed
                                    override={'dimtad': 0, 'dimasz': .2, 'dimexo': 5000, "dimtoh": 1, "dimlfac": 100},
                                    # 16MM # Moves dimension line outside if it overlaps with the circle
                                    dxfattribs={'layer': 'dimensions'}
                                ).render()
                            else:
                                msp.add_diameter_dim(
                                    center=center,
                                    radius=dot_radius,
                                    dimstyle="EZ_RADIUS",
                                    angle=135,  # Adjust the angle as needed
                                    override={'dimtad': 0, 'dimasz': .2, 'dimexo': 5000, "dimtoh": 1, "dimlfac": 100},
                                    # 12MM  # Moves dimension line outside if it overlaps with the circle
                                    dxfattribs={'layer': 'dimensions'}
                                ).render()

                    if (no_of_bars_side == 3):  # --------------------------------------------left
                        x1 = (0 + nominal_cover + side_bar / 200)
                        y1 = -4.75 * overall_depth - nominal_cover + side_bar / 200
                        y2 = -4.5 * overall_depth - nominal_cover + side_bar / 200
                        y3 = -4.25 * overall_depth - nominal_cover + side_bar / 200
                        dot_centers1 = [(x1, y1), (x1, y2), (x1, y3)]  # Replace with the actual centers of the dots
                        dot_radius1 = side_bar / 200
                        bottom = 10
                        create_dots(dot_centers1, dot_radius1, bottom)
                    elif (no_of_bars_side == 2):
                        x1 = (0 + nominal_cover + side_bar / 200)
                        y1 = -4.66 * overall_depth - nominal_cover + side_bar / 200
                        y2 = -4.33 * overall_depth - nominal_cover + side_bar / 200
                        dot_centers1 = [(x1, y2), (x1, y1)]  # Replace with the actual centers of the dots
                        dot_radius1 = side_bar / 200
                        bottom = 10
                        create_dots(dot_centers1, dot_radius1, bottom)
                    elif (no_of_bars_side == 4):
                        x1 = (0 + nominal_cover + side_bar / 200)
                        y1 = -4.8 * overall_depth - nominal_cover + side_bar / 200
                        y2 = -4.6 * overall_depth - nominal_cover + side_bar / 200
                        y3 = -4.4 * overall_depth - nominal_cover + side_bar / 200
                        y3 = -4.2 * overall_depth - nominal_cover + side_bar / 200
                        dot_centers1 = [(x1, y1), (x2, y2), (x3, y3),
                                        (x4, y4)]  # Replace with the actual centers of the dots
                        dot_radius1 = side_bar / 200
                        bottom = 10
                        create_dots(dot_centers1, dot_radius1, bottom)
                    else:
                        print("bars cannot be arranged")
                    if (no_of_bars_side == 3):  # --------------------------------------------right
                        x1 = (wall_thickness - nominal_cover - side_bar / 200)
                        y1 = -4.75 * overall_depth - nominal_cover + side_bar / 200
                        y2 = -4.5 * overall_depth - nominal_cover + side_bar / 200
                        y3 = -4.25 * overall_depth - nominal_cover + side_bar / 200
                        dot_centers1 = [(x1, y1), (x1, y2), (x1, y3)]  # Replace with the actual centers of the dots
                        dot_radius1 = side_bar / 200
                        bottom = 10
                        create_dots(dot_centers1, dot_radius1, bottom)
                    elif (no_of_bars_side == 2):
                        x1 = (wall_thickness - nominal_cover - side_bar / 200)
                        y1 = -4.66 * overall_depth - nominal_cover + side_bar / 200
                        y2 = -4.33 * overall_depth - nominal_cover + side_bar / 200
                        dot_centers1 = [(x1, y2), (x1, y1)]  # Replace with the actual centers of the dots
                        dot_radius1 = side_bar / 200
                        bottom = 10
                        create_dots(dot_centers1, dot_radius1, bottom)
                    elif (no_of_bars_side == 4):
                        x1 = (wall_thickness - nominal_cover - side_bar / 200)
                        y1 = -4.8 * overall_depth - nominal_cover + side_bar / 200
                        y2 = -4.6 * overall_depth - nominal_cover + side_bar / 200
                        y3 = -4.4 * overall_depth - nominal_cover + side_bar / 200
                        y3 = -4.2 * overall_depth - nominal_cover + side_bar / 200
                        dot_centers1 = [(x1, y1), (x1, y2), (x1, y3),
                                        (x1, y4)]  # Replace with the actual centers of the dots
                        dot_radius1 = side_bar / 200
                        bottom = 10
                        create_dots(dot_centers1, dot_radius1, bottom)
                    else:
                        print("bars cannot be arranged")
                        # ---------------for section bb
                    if (no_of_bars_side == 3):  # --------------------------------------------left-bb
                        x1 = (500 * clear_span - wall_thickness + nominal_cover + top_bar / 200)
                        y1 = -4.75 * overall_depth - nominal_cover + side_bar / 200
                        y2 = -4.5 * overall_depth - nominal_cover + side_bar / 200
                        y3 = -4.25 * overall_depth - nominal_cover + side_bar / 200
                        dot_centers1 = [(x1, y1), (x1, y2), (x1, y3)]  # Replace with the actual centers of the dots
                        dot_radius1 = side_bar / 200
                        bottom = 10
                        create_dots(dot_centers1, dot_radius1, bottom)
                    elif (no_of_bars_side == 2):
                        x1 = (500 * clear_span - wall_thickness + nominal_cover + top_bar / 200)
                        y1 = -4.66 * overall_depth - nominal_cover + side_bar / 200
                        y2 = -4.33 * overall_depth - nominal_cover + side_bar / 200
                        dot_centers1 = [(x1, y2), (x1, y1)]  # Replace with the actual centers of the dots
                        dot_radius1 = side_bar / 200
                        bottom = 10
                        create_dots(dot_centers1, dot_radius1, bottom)
                    elif (no_of_bars_side == 4):
                        x1 = (500 * clear_span - wall_thickness + nominal_cover + top_bar / 200)
                        y1 = -4.8 * overall_depth - nominal_cover + side_bar / 200
                        y2 = -4.6 * overall_depth - nominal_cover + side_bar / 200
                        y3 = -4.4 * overall_depth - nominal_cover + side_bar / 200
                        y3 = -4.2 * overall_depth - nominal_cover + side_bar / 200
                        dot_centers1 = [(x1, y1), (x2, y2), (x3, y3),
                                        (x4, y4)]  # Replace with the actual centers of the dots
                        dot_radius1 = side_bar / 200
                        bottom = 10
                        create_dots(dot_centers1, dot_radius1, bottom)
                    else:
                        print("bars cannot be arranged")
                    if (no_of_bars_side == 3):  # --------------------------------------------right -bb
                        x1 = (500 * clear_span - nominal_cover - side_bar / 200)
                        y1 = -4.75 * overall_depth - nominal_cover + side_bar / 200
                        y2 = -4.5 * overall_depth - nominal_cover + side_bar / 200
                        y3 = -4.25 * overall_depth - nominal_cover + side_bar / 200
                        dot_centers1 = [(x1, y1), (x1, y2), (x1, y3)]  # Replace with the actual centers of the dots
                        dot_radius1 = side_bar / 200
                        bottom = 10
                        create_dots(dot_centers1, dot_radius1, bottom)
                    elif (no_of_bars_side == 2):
                        x1 = (500 * clear_span - nominal_cover - side_bar / 200)
                        y1 = -4.66 * overall_depth - nominal_cover + side_bar / 200
                        y2 = -4.33 * overall_depth - nominal_cover + side_bar / 200
                        dot_centers1 = [(x1, y2), (x1, y1)]  # Replace with the actual centers of the dots
                        dot_radius1 = side_bar / 200
                        bottom = 10
                        create_dots(dot_centers1, dot_radius1, bottom)
                    elif (no_of_bars_side == 4):
                        x1 = (500 * clear_span - nominal_cover - side_bar / 200)
                        y1 = -4.8 * overall_depth - nominal_cover + side_bar / 200
                        y2 = -4.6 * overall_depth - nominal_cover + side_bar / 200
                        y3 = -4.4 * overall_depth - nominal_cover + side_bar / 200
                        y3 = -4.2 * overall_depth - nominal_cover + side_bar / 200
                        dot_centers1 = [(x1, y1), (x1, y2), (x1, y3),
                                        (x1, y4)]  # Replace with the actual centers of the dots
                        dot_radius1 = side_bar / 200
                        bottom = 10
                        create_dots(dot_centers1, dot_radius1, bottom)
                    else:
                        print("bars cannot be arranged")
                    if (no_of_bars_side == 3):  # --------------------------------------------left-bb
                        x1 = (1000 * clear_span - wall_thickness + nominal_cover + top_bar / 200)
                        y1 = -4.75 * overall_depth - nominal_cover + side_bar / 200
                        y2 = -4.5 * overall_depth - nominal_cover + side_bar / 200
                        y3 = -4.25 * overall_depth - nominal_cover + side_bar / 200
                        dot_centers1 = [(x1, y1), (x1, y2), (x1, y3)]  # Replace with the actual centers of the dots
                        dot_radius1 = side_bar / 200
                        bottom = 10
                        create_dots(dot_centers1, dot_radius1, bottom)
                    elif (no_of_bars_side == 2):
                        x1 = (1000 * clear_span - wall_thickness + nominal_cover + top_bar / 200)
                        y1 = -4.66 * overall_depth - nominal_cover + side_bar / 200
                        y2 = -4.33 * overall_depth - nominal_cover + side_bar / 200
                        dot_centers1 = [(x1, y2), (x1, y1)]  # Replace with the actual centers of the dots
                        dot_radius1 = side_bar / 200
                        bottom = 10
                        create_dots(dot_centers1, dot_radius1, bottom)
                    elif (no_of_bars_side == 4):
                        x1 = (1000 * clear_span - wall_thickness + nominal_cover + top_bar / 200)
                        y1 = -4.8 * overall_depth - nominal_cover + side_bar / 200
                        y2 = -4.6 * overall_depth - nominal_cover + side_bar / 200
                        y3 = -4.4 * overall_depth - nominal_cover + side_bar / 200
                        y3 = -4.2 * overall_depth - nominal_cover + side_bar / 200
                        dot_centers1 = [(x1, y1), (x2, y2), (x3, y3),
                                        (x4, y4)]  # Replace with the actual centers of the dots
                        dot_radius1 = side_bar / 200
                        bottom = 10
                        create_dots(dot_centers1, dot_radius1, bottom)
                    else:
                        print("bars cannot be arranged")
                    if (no_of_bars_side == 3):  # --------------------------------------------right -cc
                        x1 = (1000 * clear_span - nominal_cover - main_bar / 200)
                        y1 = -4.75 * overall_depth - nominal_cover + side_bar / 200
                        y2 = -4.5 * overall_depth - nominal_cover + side_bar / 200
                        y3 = -4.25 * overall_depth - nominal_cover + side_bar / 200
                        dot_centers1 = [(x1, y1), (x1, y2), (x1, y3)]  # Replace with the actual centers of the dots
                        dot_radius1 = side_bar / 200
                        bottom = 10
                        create_dots(dot_centers1, dot_radius1, bottom)
                    elif (no_of_bars_side == 2):
                        x1 = (1000 * clear_span - nominal_cover - main_bar / 200)
                        y1 = -4.66 * overall_depth - nominal_cover + side_bar / 200
                        y2 = -4.33 * overall_depth - nominal_cover + side_bar / 200
                        dot_centers1 = [(x1, y2), (x1, y1)]  # Replace with the actual centers of the dots
                        dot_radius1 = side_bar / 200
                        bottom = 10
                        create_dots(dot_centers1, dot_radius1, bottom)
                    elif (no_of_bars_side == 4):
                        x1 = (1000 * clear_span - nominal_cover - main_bar / 200)
                        y1 = -4.8 * overall_depth - nominal_cover + side_bar / 200
                        y2 = -4.6 * overall_depth - nominal_cover + side_bar / 200
                        y3 = -4.4 * overall_depth - nominal_cover + side_bar / 200
                        y3 = -4.2 * overall_depth - nominal_cover + side_bar / 200
                        dot_centers1 = [(x1, y1), (x1, y2), (x1, y3),
                                        (x1, y4)]  # Replace with the actual centers of the dots
                        dot_radius1 = side_bar / 200
                        bottom = 10
                        create_dots(dot_centers1, dot_radius1, bottom)
                    else:
                        print("bars cannot be arranged")
            dim.render()

            # Save the document as a DXF file
            file = "Cantilever.dxf"
            doc.saveas(file)
            print("Drwaing is created for Cantilever beam as:", file)
        else:
            ultimate_bending_moment = ubm
            b = wall_thickness
            stdia = 8
            leg = 2
            print("The section is Doubly Reinforced")
            # ---------------Ast--------------------------------------------------------------------------------------------------------------------------------

            ast1 = 0.00574712643678161 * (
                    87 * b * effective_depth * fck -
                    9.32737905308882 * (b * fck * (-400 * mul * 1000000 + 87 * b * effective_depth ** 2 * fck)) ** 0.5
            ) / fy
            # ast1 = 0.00574712643678161 * (x * (b * fck * (y)) ** 0.5) / fy
            ast2 = (-mul + ubm) * 10 ** 6 / (.87 * fy * (ed1 - ed + effective_depth))
            ast = ast1 + ast2
            print("ast 1: ", ast1)
            print("ast 2: ", ast2)
            print("ast", ast)
            astmin = 0.85 * b * effective_depth / fy
            print("breath", b)
            print("astmin", astmin)
            astmax = .04 * b * provided_depth
            print("Maximum Ast:", astmax)
            ast=max(ast,astmin)
            if (astmax > astmin or astmax > ast):
                return("Revise Section")
                sys.exit()
            # --------------------------------------Top bars-----------------------------------------------------------------------------------------------------
            if (ast > astmin):
                print("Ast will be governing for steel arrangement")
                main_bar = [12, 16, 20, 25, 32, 40]
                results = []
                for num in main_bar:
                    # Calculate the result
                    result = max(ast / (num * num * .785), 2)
                    results.append((num, math.ceil(result)))

                # Find suitable bar and count
                suitable_bars = [(num, count) for num, count in results if 2 <= count < 5]
                if suitable_bars:
                    main_bar, no_of_bars_top = suitable_bars[0]  # Select the first suitable option
                else:
                    main_bar, no_of_bars_top = (0, 0)  # Default to zero if no suitable option is found

                # Calculate the area of steel provided and percentage
                ab = no_of_bars_top * 0.78539816339744830961566084581988 * main_bar ** 2
                pt = 100 * ab / (b * effective_depth)

                # print(main_bar, no_of_bars, pt)
                main_bar_provided = main_bar
                # no_of_bars = round(ast / (0.78539816339744830961566084581988 * main_bar ** 2), 0)
                print("provide", no_of_bars_top, "-Φ", main_bar, " mm as main bars at the top")
                # ab = no_of_bars * 0.78539816339744830961566084581988 * main_bar ** 2
                # pt = 100 * ab / (b * effective_depth)
                print("percentage of steel provided(Tension Reinforcement): ", pt)
            else:
                main_bar = [12, 16, 20, 25, 32, 40]
                results = []
                for num in main_bar:
                    # Calculate the result
                    result = max(astmin / (num * num * .785), 2)
                    results.append((num, math.ceil(result)))

                # Find suitable bar and count
                suitable_bars = [(num, count) for num, count in results if 2 <= count < 5]
                if suitable_bars:
                    main_bar, no_of_bars_top = suitable_bars[0]  # Select the first suitable option
                else:
                    main_bar, no_of_bars_top = (0, 0)  # Default to zero if no suitable option is found

                # Calculate the area of steel provided and percentage
                ab = no_of_bars_top * 0.78539816339744830961566084581988 * main_bar ** 2
                pt = 100 * ab / (b * effective_depth)

                # print(main_bar, no_of_bars, pt)
                main_bar_provided = main_bar
                # no_of_bars = round(ast / (0.78539816339744830961566084581988 * main_bar ** 2), 0)
                print("provide", no_of_bars_top, "-Φ", main_bar, " mm as main bars at the top")
                # ab = no_of_bars * 0.78539816339744830961566084581988 * main_bar ** 2
                # pt = 100 * ab / (b * effective_depth)
                print("percentage of steel provided(Tension Reinforcement): ", pt)
            # -----------------------------------bottom bars---------------------------------------
            if (astmin < ast2):
                bottom_bar = [12, 16, 20, 25, 32, 40]
                results1 = []
                for num in bottom_bar:
                    # Calculate the result
                    result1 = max(ast2 / (num * num * .785), 2)
                    results1.append((num, math.ceil(result1)))

                # Find suitable bar and count-----------------------------------------------------
                suitable_bars = [(num, count) for num, count in results1 if 2 <= count < 5]
                if suitable_bars:
                    bottom_bar, no_of_bars_bottom = suitable_bars[0]  # Select the first suitable option
                else:
                    bottom_bar, no_of_bars_bottom = (0, 0)  # Default to zero if no suitable option is found
                if (no_of_bars_bottom == 0):
                    no_of_bars_bottom = 2
                    bottom_bar = 12

                # Calculate the area of steel provided and percentage------------------------------------------
                ab = no_of_bars_bottom * 0.78539816339744830961566084581988 * bottom_bar ** 2
                pt = 100 * ab / (b * effective_depth)

                # print(main_bar, no_of_bars, pt)
                bottom_bar_provided = bottom_bar
                # no_of_bars = round(ast / (0.78539816339744830961566084581988 * main_bar ** 2), 0)
                print("provide", no_of_bars_bottom, "-Φ", bottom_bar, " mm as main bars at the bottom")

                print("percentage of steel provided(Compression Reinforcement): ", pt)
            else:
                bottom_bar = [12, 16, 20, 25, 32, 40]
                results1 = []
                for num in bottom_bar:
                    # Calculate the result
                    result1 = max(astmin / (num * num * .785), 2)
                    results1.append((num, math.ceil(result1)))

                # Find suitable bar and count-----------------------------------------------------
                suitable_bars = [(num, count) for num, count in results1 if 2 <= count < 5]
                if suitable_bars:
                    bottom_bar, no_of_bars_bottom = suitable_bars[0]  # Select the first suitable option
                else:
                    bottom_bar, no_of_bars_bottom = (0, 0)  # Default to zero if no suitable option is found
                if (no_of_bars_bottom == 0):
                    no_of_bars_bottom = 2
                    bottom_bar = 12

                # Calculate the area of steel provided and percentage------------------------------------------
                ab = no_of_bars_bottom * 0.78539816339744830961566084581988 * bottom_bar ** 2
                pt = 100 * ab / (b * effective_depth)

                # print(main_bar, no_of_bars, pt)
                bottom_bar_provided = bottom_bar
                # no_of_bars = round(ast / (0.78539816339744830961566084581988 * main_bar ** 2), 0)
                print("provide", no_of_bars_bottom, "-Φ", bottom_bar, " mm as main bars at the bottom")

                print("percentage of steel provided(Compression Reinforcement): ", pt)
            #side face
            if provided_depth > 750:
                sideast = 0.0005 * wall_thickness *  provided_depth
                side_bar = [12, 16, 20, 25, 32, 40]
                results1 = []
                print(sideast)
                # Calculate the required number of bars for each available diameter
                for num in side_bar:
                    # Calculate the result
                    required_area_per_bar = max(sideast / (num * num * 0.785), 2)
                    # Store the diameter and the required number of bars (rounded up)
                    results1.append((num, math.ceil(required_area_per_bar)))

                # Find suitable bars and count
                suitable_bars = [(num, count) for num, count in results1 if 1 <= count < 5]
                if suitable_bars:
                    side_bar, no_of_bars_side = suitable_bars[0]  # Select the first suitable option
                else:
                    side_bar, no_of_bars_side = (12, 1)  # Default to 12mm bar and 1 bar if no suitable option is found

                # Print the result
                print("Provide", no_of_bars_side, "no of", side_bar, "mm bars on each side of the beam")
            # --------------------------check for shear-----------------------------------------------------
            ultimate_shear_force = usf
            vu = ultimate_shear_force * 1000
            tv = vu / (b * effective_depth)
            print(effective_depth)
            p = 100 * ast / (b * effective_depth)
            # print(p)

            beta = 0.8 * fck / (6.89 * p)
            f = (0.8 * fck) ** 0.5
            brta = ((1 + 5 * beta) ** 0.5) - 1
            tc = 0.85 * f * brta / (6 * beta)
            # tc=(0.85*((0.8*fck)**0.5)*((1+5*beta)**0.5)-1)/(6*beta)
            print("tc value: ", tc)
            print("tv value: ", tv)
            if (tv > tc and tv <= tcmax):
                Vus = ultimate_shear_force * 1000 - (tc * b * effective_depth)
                print("Vus value: ", Vus)
                stdia = int(input("enter the diameter of the stirrup in mm: ") or 8)
                leg = int(input("enter the number of legs for the stirrups: ") or 2)

                sv = 0.87 * fy * effective_depth * leg * 0.78539816339744830961566084581988 * stdia ** 2 / Vus
                print(sv)
                spacing = min(0.75 * effective_depth, 300)
                max_spacing = (spacing // 25) * 25
                # print(max_spacing)
                print("Provide Φ", stdia, "- mm ", leg, "vertical stirrups @", max_spacing, "c/c")
            elif (tv <= tc):
                stdia = int(input("enter the diameter of the stirrup in mm: ") or 8)
                leg = int(input("enter the number of legs for the stirrups: ") or 2)

                sv = 0.87 * fy * leg * 0.78539816339744830961566084581988 * stdia ** 2 / (0.4 * wall_thickness)
                spacing = min(0.75 * effective_depth, 300)
                max_spacing = (spacing // 25) * 25
                # print(max_spacing)
                print("Provide Φ", stdia, "- mm ", leg, "vertical stirrups @", max_spacing, "c/c")
            else:
                return("revise section (per Cl. 40.2.3, IS 456: 2000, pp. 72")
            # step 6:Check for Deflection---------------------
            l = revised_effective_length
            Actualspan = l / effective_depth
            bd = b * effective_depth / (100 * ast)
            fs = 0.58 * fy * ast / (no_of_bars_top * 0.78539816339744830961566084581988 * main_bar ** 2)

            mf = 1 / (0.225 + 0.003228 * fs - 0.625 * math.log10(bd))
            allowablespan = 7 * mf
            print("modification factor: ", mf)
            # ----------------------------------------development length------------------------------------------
            phi = main_bar
            # print(main_bar)
            # print(bottom_bar)
            tss = 0.87 * fy
            if (fck == 20):
                tbd = 1.2 * 1.6
            elif (fck == 25):
                tbd = 1.4 * 2.24
            elif (fck == 30):
                tbd = 1.5 * 2.4
            elif (fck == 35):
                tbd = 1.7 * 2.72
            elif (fck >= 40):
                tbd = 1.9 * 3.04
            ld = phi * tss / (4 * tbd)
            print("Provide Devlopment Length: ", ld, "mm")
            # ---------------shear reinforcement--------------------
            as1 = 0.1 * wall_thickness * effective_depth / 100
            print("as1", as1)
            x = int(input("Enter the diameter for shear reinforcement") or 10)
            no_of_bars_shear_face = math.ceil((as1 / 2) / (0.785 * x))
            spacing_of_bars = provided_depth - nominal_cover * 2 - stdia * 2 - main_bar / 2 - bottom_bar_provided / 2
            no_of_bars_shear = math.ceil((spacing_of_bars / wall_thickness) - 1)
            print("shear r", no_of_bars_shear)
            if (allowablespan > Actualspan):
                print(" The section is safe under deflection")
            else:
                return(" revise section")
            no_bars_top = no_of_bars_top
            top_bar = main_bar
            print("bot dia", bottom_bar)
            print("top dia", top_bar)
            effective_cover = ed1 - ed
            stdia = stdia
            clear_span = clear_span / 100
            wall_thickness = wall_thickness / 100
            overall_depth = provided_depth / 100
            revised_effective_length = beam_length / 100
            cd = cd / 100
            temp = no_of_bars_bottom
            no_of_bars_bottom = no_of_bars_top
            no_of_bars_top = temp

            # print(clear_span)
            # Initiate DXF file and access model space
            doc = ezdxf.new(setup=True)
            msp = doc.modelspace()
            dimstyle = doc.dimstyles.new("MyCustomStyle")
            dimstyle.dxf.dimasz = 0.5
            dimstyle.dxf.dimtxt = .1
            # dimstyle.dxf.dim
            # which is a shortcut (including validation) for
            doc.header['$INSUNITS'] = units.MM

            x = -cd + nominal_cover / 100
            y = overall_depth - nominal_cover / 100
            x1 = clear_span * 1000 - nominal_cover / 100
            x11 = clear_span * 100
            y1 = overall_depth - nominal_cover / 100
            x3 = -cd + nominal_cover / 100
            x31 = clear_span * 800
            y3 = nominal_cover / 100
            x4 = clear_span * 1000 + - nominal_cover / 100
            y4 = nominal_cover / 100
            x5 = -wall_thickness / 2
            y5 = overall_depth / 1.2
            x6 = clear_span * 1000 + 2 * wall_thickness / 4
            y6 = overall_depth / 1.2

            # Create a Line
            msp.add_line((x, y), (x1, y1))  # top bar
            msp.add_line((x, y), (x, -ld / 100))
            msp.add_line((x3, y3), (x4, y4))  # bottom bar
            msp.add_line((0, 0), (clear_span * 1000, 0))
            msp.add_line((0, 0), (-cd, 0))
            msp.add_line((-cd, 0), (-cd, overall_depth))
            msp.add_line((-cd, overall_depth), (0, overall_depth))
            msp.add_line((-cd, 0), (-cd, -overall_depth))
            msp.add_line((-cd, -overall_depth), (0, -overall_depth))
            msp.add_line((-cd, overall_depth), (-cd, 2 * overall_depth))  # ------uppper wall
            msp.add_line((-cd, 2 * overall_depth), (0, 2 * overall_depth))
            msp.add_line((0, 2 * overall_depth), (0, overall_depth))  # ------upper wall
            msp.add_line((0, -overall_depth), (0, 0))
            # msp.add_line((0,0),(0,overall_depth))
            msp.add_line((0, overall_depth), (clear_span * 1000, overall_depth))
            msp.add_line((clear_span * 1000, overall_depth), (clear_span * 1000, 0))
            # msp.add_line((clear_span * 1000, 0), (clear_span * 1000, -overall_depth))
            # msp.add_line((clear_span * 1000, -overall_depth), (clear_span * 1000 + wall_thickness, -overall_depth))
            # msp.add_line((clear_span * 1000 + wall_thickness, -overall_depth),(clear_span * 1000 + wall_thickness, overall_depth))
            msp.add_line((clear_span * 500, 0), (clear_span * 500, overall_depth))
            # cross-section
            msp.add_line((0, -5 * overall_depth), (wall_thickness, -5 * overall_depth))  # bottom line
            msp.add_line((0, -5 * overall_depth), (0, -4 * overall_depth))  # left line
            msp.add_line((0, -4 * overall_depth), (wall_thickness, -4 * overall_depth))
            msp.add_line((wall_thickness, -4 * overall_depth), (wall_thickness, -5 * overall_depth))
            # --stirrup cross
            nominal_cover = nominal_cover / 100
            msp.add_line((0 + nominal_cover, -5 * overall_depth + nominal_cover),
                         (wall_thickness - nominal_cover, -5 * overall_depth + nominal_cover))  # bottom line
            msp.add_line((0 + nominal_cover, -5 * overall_depth + nominal_cover),
                         (0 + nominal_cover, -4 * overall_depth - nominal_cover))  # left line
            msp.add_line((0 + nominal_cover, -4 * overall_depth - nominal_cover),
                         (wall_thickness - nominal_cover, -4 * overall_depth - nominal_cover))
            msp.add_line((wall_thickness - nominal_cover, -4 * overall_depth - nominal_cover),
                         (wall_thickness - nominal_cover, -5 * overall_depth + nominal_cover))
            ml_builder = msp.add_multileader_mtext("Standard")

            ct = "Provide", no_of_bars_bottom, "Φ", bottom_bar, "- mm as \n main bars at the bottom"
            content_str = ', '.join(map(str, ct))
            ml_builder.set_content(content_str, style="OpenSans", char_height=.7,
                                   alignment=mleader.TextAlignment.center, )

            X22 = clear_span * 900
            X11 = clear_span * 50
            ml_builder.add_leader_line(mleader.ConnectionSide.left, [Vec2(X11, y4)])
            ml_builder.add_leader_line(mleader.ConnectionSide.right, [Vec2(X22, y4)])
            ml_builder.build(insert=Vec2(clear_span * 500, -1 * overall_depth))

            # -----top bar
            ml_builder1 = msp.add_multileader_mtext("Standard")
            content_str1 = "Provide", no_of_bars_top, "-Φ", top_bar, "- mm \n as main bars at the top"
            content_str1 = ', '.join(map(str, content_str1))
            ml_builder1.set_content(content_str1, style="OpenSans", char_height=.7,
                                    alignment=mleader.TextAlignment.center, )
            X32 = clear_span * 50
            X31 = clear_span * 900
            ml_builder1.add_leader_line(mleader.ConnectionSide.right, [Vec2(X31, y1)])
            ml_builder1.add_leader_line(mleader.ConnectionSide.left, [Vec2(X32, y1)])
            ml_builder1.build(insert=Vec2(500 * clear_span, 1.5 * overall_depth))
            # ----striupp
            ml_builder2 = msp.add_multileader_mtext("Standard")
            content_str3 = "Provide Φ", stdia, " -mm", leg, "\n" " legged vertical stirrups @", max_spacing, "c/c"
            content_str3 = ', '.join(map(str, content_str3))
            ml_builder2.set_content(
                content_str3,
                style="OpenSans",
                char_height=1,
                alignment=mleader.TextAlignment.left,  # set MTEXT alignment!
            )
            X6 = clear_span * 1000
            Y6 = overall_depth
            ml_builder2.add_leader_line(mleader.ConnectionSide.left, [Vec2(X6 / 2, Y6 / 2)])
            ml_builder2.build(insert=Vec2(clear_span * 800, 2 * overall_depth))
            # dimensions
            # Adda horizontal linear DIMENSION entity:
            dimstyle = doc.dimstyles.get("EZDXF")
            dimstyle.dxf.dimtxt = 1
            dim = msp.add_linear_dim(
                base=(0, -2 * overall_depth),  # location of the dimension line
                p1=(0, 0),  # 1st measurement point
                p2=(clear_span * 1000, 0),  # 2nd measurement point
                dimstyle="EZDXF",  # default dimension style
            )
            dim1 = msp.add_linear_dim(
                base=(0, -2 * overall_depth),  # location of the dimension line
                p1=(-cd, -overall_depth),  # 1st measurement point
                p2=(0, -overall_depth),  # 2nd measurement point
                dimstyle="EZDXF",  # default dimension style
            )

            # hatch
            hatch = msp.add_hatch()
            hatch.set_pattern_fill("ANSI32", scale=.1)
            hatch.paths.add_polyline_path(
                [(0, 0), (-cd, 0), (-cd, -overall_depth), (0, -overall_depth)], is_closed=True
            )
            hatch1 = msp.add_hatch()
            hatch1.set_pattern_fill("ANSI32", scale=.1)
            hatch1.paths.add_polyline_path(
                [(-cd, overall_depth), (-cd, 2 * overall_depth),
                 (0, 2 * overall_depth), (0, overall_depth)], is_closed=True
            )

            def create_dots(dot_centers, dot_radius, top):
                # Create a new DXF document

                # Create solid dots at specified centers with given radius
                for center in dot_centers:
                    # Create a HATCH entity with a solid fill
                    hatch = msp.add_hatch()
                    # Add a circular path to the hatch as its boundary
                    edge_path = hatch.paths.add_edge_path()
                    edge_path.add_arc(center=center, radius=dot_radius, start_angle=0, end_angle=360)
                    # Set the hatch pattern to solid
                    hatch.set_solid_fill()
                    if (top == 1):
                        msp.add_diameter_dim(
                            center=center,
                            radius=dot_radius,
                            # text=None,
                            dimstyle="EZ_RADIUS",
                            angle=135,  # Adjust the angle as needed
                            override={'dimtad': 0, 'dimasz': .2, 'dimexo': 5000, "dimtoh": 1, "dimlfac": 100},
                            # 16MM # Moves dimension line outside if it overlaps with the circle
                            dxfattribs={'layer': 'dimensions'}
                        ).render()
                    else:
                        msp.add_diameter_dim(
                            center=center,
                            radius=dot_radius,
                            dimstyle="EZ_RADIUS",
                            angle=135,  # Adjust the angle as needed
                            override={'dimtad': 0, 'dimasz': .2, 'dimexo': 5000, "dimtoh": 1, "dimlfac": 100},
                            # 12MM  # Moves dimension line outside if it overlaps with the circle
                            dxfattribs={'layer': 'dimensions'}
                        ).render()

                # Create a rectangle from the provided corners
                # Assuming rectangle_corners is a list of tuples [(x1, y1), (x2, y2), (x3, y3), (x4, y4)] in consecutive order
                # Save the document

            # Exam
            no_bars_top = no_of_bars_top
            if (no_bars_top == 3):
                cx1 = (0 + nominal_cover + top_bar / 200)
                cx2 = ((0 + nominal_cover + top_bar / 200 + 0 + wall_thickness - nominal_cover - top_bar / 200)) / 2
                cx3 = (0 + wall_thickness - nominal_cover - top_bar / 200)
                cy1 = -4 * overall_depth - nominal_cover - top_bar / 200
                dot_centers = [(cx1, cy1), (cx2, cy1), (cx3, cy1)]  # Replace with the actual centers of the dots
                dot_radius = top_bar / 200
                top = 1
                create_dots(dot_centers, dot_radius, top)

            elif (no_bars_top == 2):
                cx1 = (0 + nominal_cover + top_bar / 200)
                cx3 = (0 + wall_thickness - nominal_cover - top_bar / 200)
                cy1 = -4 * overall_depth - nominal_cover - top_bar / 200
                dot_centers = [(cx1, cy1), (cx3, cy1)]  # Replace with the actual centers of the dots
                dot_radius = top_bar / 200
                top = 1
                create_dots(dot_centers, dot_radius, top)

            elif (no_bars_top == 4):
                cx1 = (0 + nominal_cover + top_bar / 200)
                cx2 = (wall_thickness - nominal_cover * 2) / 3 + nominal_cover
                cx3 = 2 * (wall_thickness - nominal_cover * 2) / 3 + nominal_cover
                cx4 = (0 + wall_thickness - nominal_cover - top_bar / 200)
                cy1 = -4 * overall_depth - nominal_cover - top_bar / 200
                dot_centers = [(cx1, cy1), (cx2, cy1), (cx3, cy1),
                               (cx4, cy1)]  # Replace with the actual centers of the dots
                dot_radius = top_bar / 200
                top = 1
                create_dots(dot_centers, dot_radius, top)

            else:
                print("bars cannot be arranged")

            main_bar = bottom_bar
            if (no_of_bars_bottom == 3):  # --------------------------------------------bottom
                x1 = (0 + nominal_cover + main_bar / 200)
                x2 = ((0 + nominal_cover + main_bar / 200 + 0 + wall_thickness - nominal_cover - main_bar / 200)) / 2
                x3 = (0 + wall_thickness - nominal_cover - main_bar / 200)
                y2 = -5 * overall_depth + nominal_cover + main_bar / 200
                dot_centers1 = [(x1, y2), (x2, y2), (x3, y2)]  # Replace with the actual centers of the dots
                dot_radius1 = main_bar / 200
                bottom = 10
                create_dots(dot_centers1, dot_radius1, bottom)
            elif (no_of_bars_bottom == 2):
                x1 = (0 + nominal_cover + main_bar / 200)
                x3 = (0 + wall_thickness - nominal_cover - main_bar / 200)
                y2 = -5 * overall_depth + nominal_cover + main_bar / 200
                dot_centers1 = [(x1, y2), (x3, y2)]  # Replace with the actual centers of the dots
                dot_radius1 = main_bar / 200
                bottom = 10
                create_dots(dot_centers1, dot_radius1, bottom)
            elif (no_of_bars_bottom == 4):
                x1 = (0 + nominal_cover + main_bar / 200)
                x2 = (wall_thickness - nominal_cover * 2) / 3 + nominal_cover
                x3 = 2 * (wall_thickness - nominal_cover * 2) / 3 + nominal_cover
                x4 = (0 + wall_thickness - nominal_cover - main_bar / 200)
                y2 = -5 * overall_depth + nominal_cover + main_bar / 200
                dot_centers1 = [(x1, y2), (x2, y2), (x3, y2), (x4, y2)]  # Replace with the actual centers of the dots
                dot_radius1 = main_bar / 200
                bottom = 10
                create_dots(dot_centers1, dot_radius1, bottom)
            else:
                print("bars cannot be arranged")

            # cross section dimension
            dim3 = msp.add_linear_dim(
                base=(0, -5.5 * overall_depth),  # location of the dimension line
                p1=(0, -4 * overall_depth),  # 1st measurement point
                p2=(wall_thickness, -4 * overall_depth),  # 2nd measurement point
                dimstyle="EZDXF",  # default dimension style
            )
            msp.add_linear_dim(base=(-1 * wall_thickness, -3.5 * overall_depth), p1=(0, -4 * overall_depth),
                               p2=(0, -5 * overall_depth), angle=90).render()  # cross section
            # msp.add_linear_dim(base=(1.1*clear_span*1000, overall_depth/2), p1=(1.2*clear_span*1000, 0), p2=(1.2*clear_span*1000, overall_depth), angle=90).render()
            msp.add_linear_dim(base=(-2 * cd, overall_depth / 2), p1=(-cd, 0),
                               p2=(-cd, overall_depth), angle=90).render()  # overall depth dim

            text_string = "LONGITUDINAL SECTION (all units are in mm)"
            insert_point = (100 * clear_span, -3 * overall_depth)  # X, Y coordinates where the text will be inserted.
            text_height = 1  # Height of the text.

            # Add text to the modelspace.
            msp.add_text(
                text_string,
                dxfattribs={
                    'insert': insert_point,
                    'height': text_height,
                    # Additional attributes such as font, rotation, and color can be specified here.
                    'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                    'rotation': 0,
                    'color': 7
                }
            )

            text_string = "SECTION A-A"
            insert_point = (-wall_thickness, -7 * overall_depth)  # X, Y coordinates where the text will be inserted.
            text_height = 1
            # Add text to the modelspace.
            msp.add_text(
                text_string,
                dxfattribs={
                    'insert': insert_point,
                    'height': text_height,
                    # Additional attributes such as font, rotation, and color can be specified here.
                    'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                    'rotation': 0,
                    'color': 7
                }
            )
            text_string = "SECTION B-B"
            insert_point = (400 * clear_span, -7 * overall_depth)  # X, Y coordinates where the text will be inserted.
            text_height = 1
            # Add text to the modelspace.
            msp.add_text(
                text_string,
                dxfattribs={
                    'insert': insert_point,
                    'height': text_height,
                    # Additional attributes such as font, rotation, and color can be specified here.
                    'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                    'rotation': 0,
                    'color': 7
                }
            )
            # section b-b
            msp.add_line((500 * clear_span, -5 * overall_depth),
                         (500 * clear_span - wall_thickness, -5 * overall_depth))  # bottom line
            msp.add_line((500 * clear_span - wall_thickness, -5 * overall_depth),
                         (500 * clear_span - wall_thickness, -4 * overall_depth))  # left line
            msp.add_line((500 * clear_span - wall_thickness, -4 * overall_depth),
                         (500 * clear_span, -4 * overall_depth))
            msp.add_line((500 * clear_span, -4 * overall_depth), (500 * clear_span, -5 * overall_depth))
            # --stirrup cross
            nominal_cover = nominal_cover
            msp.add_line((500 * clear_span - nominal_cover, -5 * overall_depth + nominal_cover),
                         (500 * clear_span - wall_thickness + nominal_cover,
                          -5 * overall_depth + nominal_cover))  # bottom line
            msp.add_line((500 * clear_span - wall_thickness + nominal_cover, -5 * overall_depth + nominal_cover),
                         (500 * clear_span - wall_thickness + nominal_cover,
                          -4 * overall_depth - nominal_cover))  # left line
            msp.add_line((500 * clear_span - wall_thickness + nominal_cover, -4 * overall_depth - nominal_cover),
                         (500 * clear_span - nominal_cover, -4 * overall_depth - nominal_cover))
            msp.add_line((500 * clear_span - nominal_cover, -4 * overall_depth - nominal_cover),
                         (500 * clear_span - nominal_cover, -5 * overall_depth + nominal_cover))

            # cross section dimension
            dim3 = msp.add_linear_dim(
                base=(400 * clear_span, -5.5 * overall_depth),  # location of the dimension line
                p1=(500 * clear_span, -5 * overall_depth),  # 1st measurement point
                p2=(500 * clear_span - wall_thickness, -5 * overall_depth),  # 2nd measurement point
                dimstyle="EZDXF",  # default dimension style
            )
            msp.add_linear_dim(base=(300 * clear_span, -3.5 * overall_depth),
                               p1=(500 * clear_span - wall_thickness, -5 * overall_depth),
                               p2=(500 * clear_span - wall_thickness, -4 * overall_depth),
                               angle=90).render()  # cross section

            def create_dots_bb(dot_centers, dot_radius, top):
                # Create solid dots at specified centers with given radius
                for center in dot_centers:
                    # Create a HATCH entity with a solid fill
                    hatch = msp.add_hatch()
                    # Add a circular path to the hatch as its boundary
                    edge_path = hatch.paths.add_edge_path()
                    edge_path.add_arc(center=center, radius=dot_radius, start_angle=0, end_angle=360)
                    # Set the hatch pattern to solid
                    hatch.set_solid_fill()
                    if (top == 1):
                        msp.add_diameter_dim(
                            center=center,
                            radius=dot_radius,
                            # text=None,
                            dimstyle="EZ_RADIUS",
                            angle=135,  # Adjust the angle as needed
                            override={'dimtad': 0, 'dimasz': .2, 'dimexo': 5000, "dimtoh": 1, "dimlfac": 100},
                            # 16MM # Moves dimension line outside if it overlaps with the circle
                            dxfattribs={'layer': 'dimensions'}
                        ).render()
                    else:
                        msp.add_diameter_dim(
                            center=center,
                            radius=dot_radius,
                            dimstyle="EZ_RADIUS",
                            angle=135,  # Adjust the angle as needed
                            override={'dimtad': 0, 'dimasz': .2, 'dimexo': 5000, "dimtoh": 1, "dimlfac": 100},
                            # 12MM  # Moves dimension line outside if it overlaps with the circle
                            dxfattribs={'layer': 'dimensions'}
                        ).render()

                # Create a rectangle from the provided corners
                # Assuming rectangle_corners is a list of tuples [(x1, y1), (x2, y2), (x3, y3), (x4, y4)] in consecutive order
                # Save the document

            # Exam

            if (no_bars_top == 3):
                cx1 = (500 * clear_span - wall_thickness + nominal_cover + top_bar / 200)
                cx2 = ((
                        500 * clear_span - wall_thickness + nominal_cover + top_bar / 200 + 500 * clear_span - nominal_cover - top_bar / 200)) / 2
                cx3 = (500 * clear_span - nominal_cover - top_bar / 200)
                cy1 = -4 * overall_depth - nominal_cover - top_bar / 200
                dot_centers = [(cx1, cy1), (cx2, cy1), (cx3, cy1)]  # Replace with the actual centers of the dots
                dot_radius = top_bar / 200
                top = 1
                create_dots_bb(dot_centers, dot_radius, top)

            elif (no_bars_top == 2):
                cx1 = (500 * clear_span - wall_thickness + nominal_cover + top_bar / 200)
                cx3 = (500 * clear_span - nominal_cover - top_bar / 200)
                cy1 = -4 * overall_depth - nominal_cover - top_bar / 200
                dot_centers = [(cx1, cy1), (cx3, cy1)]  # Replace with the actual centers of the dots
                dot_radius = top_bar / 200
                top = 1
                create_dots_bb(dot_centers, dot_radius, top)

            elif (no_bars_top == 4):
                cx1 = (500 * clear_span - wall_thickness + nominal_cover + top_bar / 200)
                cx2 = (500 * clear_span - wall_thickness + wall_thickness / 3 + top_bar / 200)
                cx3 = (500 * clear_span - wall_thickness + 2 * wall_thickness / 3 - top_bar / 200)
                cx4 = (500 * clear_span - nominal_cover - top_bar / 200)
                cy1 = -4 * overall_depth - nominal_cover - top_bar / 200
                dot_centers = [(cx1, cy1), (cx2, cy1), (cx3, cy1),
                               (cx4, cy1)]  # Replace with the actual centers of the dots
                dot_radius = top_bar / 200
                top = 1
                create_dots_bb(dot_centers, dot_radius, top)

            else:
                print("bars cannot be arranged")

            if (no_of_bars_bottom == 3):  # --------------------------------------------bottom
                x1 = (500 * clear_span - wall_thickness + nominal_cover + main_bar / 200)
                x2 = ((
                        500 * clear_span - wall_thickness + nominal_cover + main_bar / 200 + 500 * clear_span - nominal_cover - main_bar / 200)) / 2
                x3 = (500 * clear_span - nominal_cover - main_bar / 200)
                y2 = -5 * overall_depth + nominal_cover + main_bar / 200
                dot_centers1 = [(x1, y2), (x2, y2), (x3, y2)]  # Replace with the actual centers of the dots
                dot_radius1 = main_bar / 200
                bottom = 10
                create_dots_bb(dot_centers1, dot_radius1, bottom)
            elif (no_of_bars_bottom == 2):
                x1 = (500 * clear_span - wall_thickness + nominal_cover + main_bar / 200)
                x3 = (500 * clear_span - nominal_cover - main_bar / 200)
                y2 = -5 * overall_depth + nominal_cover + main_bar / 200
                dot_centers1 = [(x1, y2), (x3, y2)]  # Replace with the actual centers of the dots
                dot_radius1 = main_bar / 200
                bottom = 10
                create_dots_bb(dot_centers1, dot_radius1, bottom)
            elif (no_of_bars_bottom == 4):
                x1 = (500 * clear_span - wall_thickness + nominal_cover + main_bar / 200)
                x2 = (500 * clear_span - wall_thickness + wall_thickness / 3) + main_bar / 200
                x3 = (500 * clear_span - wall_thickness + 2 * wall_thickness / 3) - main_bar / 200
                x4 = (500 * clear_span - nominal_cover - main_bar / 200)
                y2 = -5 * overall_depth + nominal_cover + main_bar / 200
                dot_centers1 = [(x1, y2), (x2, y2), (x3, y2), (x4, y2)]  # Replace with the actual centers of the dots
                dot_radius1 = main_bar / 200
                bottom = 10
                create_dots_bb(dot_centers1, dot_radius1, bottom)
            else:
                print("bars cannot be arranged")
            text_string = "SECTION C-C"
            insert_point = (1000 * clear_span, -7 * overall_depth)  # X, Y coordinates where the text will be inserted.
            text_height = 1
            # Add text to the modelspace.
            msp.add_text(
                text_string,
                dxfattribs={
                    'insert': insert_point,
                    'height': text_height,
                    # Additional attributes such as font, rotation, and color can be specified here.
                    'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                    'rotation': 0,
                    'color': 7
                }
            )
            # section b-b
            msp.add_line((1000 * clear_span, -5 * overall_depth),
                         (1000 * clear_span - wall_thickness, -5 * overall_depth))  # bottom line
            msp.add_line((1000 * clear_span - wall_thickness, -5 * overall_depth),
                         (1000 * clear_span - wall_thickness, -4 * overall_depth))  # left line
            msp.add_line((1000 * clear_span - wall_thickness, -4 * overall_depth),
                         (1000 * clear_span, -4 * overall_depth))
            msp.add_line((1000 * clear_span, -4 * overall_depth), (1000 * clear_span, -5 * overall_depth))
            # --stirrup cross
            nominal_cover = nominal_cover
            msp.add_line((1000 * clear_span - nominal_cover, -5 * overall_depth + nominal_cover),
                         (1000 * clear_span - wall_thickness + nominal_cover,
                          -5 * overall_depth + nominal_cover))  # bottom line
            msp.add_line((1000 * clear_span - wall_thickness + nominal_cover, -5 * overall_depth + nominal_cover),
                         (1000 * clear_span - wall_thickness + nominal_cover,
                          -4 * overall_depth - nominal_cover))  # left line
            msp.add_line((1000 * clear_span - wall_thickness + nominal_cover, -4 * overall_depth - nominal_cover),
                         (1000 * clear_span - nominal_cover, -4 * overall_depth - nominal_cover))
            msp.add_line((1000 * clear_span - nominal_cover, -4 * overall_depth - nominal_cover),
                         (1000 * clear_span - nominal_cover, -5 * overall_depth + nominal_cover))

            # cross section dimension
            dim3 = msp.add_linear_dim(
                base=(900 * clear_span, -5.5 * overall_depth),  # location of the dimension line
                p1=(1000 * clear_span, -5 * overall_depth),  # 1st measurement point
                p2=(1000 * clear_span - wall_thickness, -5 * overall_depth),  # 2nd measurement point
                dimstyle="EZDXF",  # default dimension style
            )
            msp.add_linear_dim(base=(900 * clear_span, -3.5 * overall_depth),
                               p1=(1000 * clear_span - wall_thickness, -5 * overall_depth),
                               p2=(1000 * clear_span - wall_thickness, -4 * overall_depth),
                               angle=90).render()  # cross section

            def create_dots_cc(dot_centers, dot_radius, top):
                # Create solid dots at specified centers with given radius
                for center in dot_centers:
                    # Create a HATCH entity with a solid fill
                    hatch = msp.add_hatch()
                    # Add a circular path to the hatch as its boundary
                    edge_path = hatch.paths.add_edge_path()
                    edge_path.add_arc(center=center, radius=dot_radius, start_angle=0, end_angle=360)
                    # Set the hatch pattern to solid
                    hatch.set_solid_fill()
                    if (top == 1):
                        msp.add_diameter_dim(
                            center=center,
                            radius=dot_radius,
                            # text=None,
                            dimstyle="EZ_RADIUS",
                            angle=135,  # Adjust the angle as needed
                            override={'dimtad': 0, 'dimasz': .2, 'dimexo': 5000, "dimtoh": 1, "dimlfac": 100},
                            # 16MM # Moves dimension line outside if it overlaps with the circle
                            dxfattribs={'layer': 'dimensions'}
                        ).render()
                    else:
                        msp.add_diameter_dim(
                            center=center,
                            radius=dot_radius,
                            dimstyle="EZ_RADIUS",
                            angle=135,  # Adjust the angle as needed
                            override={'dimtad': 0, 'dimasz': .2, 'dimexo': 5000, "dimtoh": 1, "dimlfac": 100},
                            # 12MM  # Moves dimension line outside if it overlaps with the circle
                            dxfattribs={'layer': 'dimensions'}
                        ).render()

                # Create a rectangle from the provided corners
                # Assuming rectangle_corners is a list of tuples [(x1, y1), (x2, y2), (x3, y3), (x4, y4)] in consecutive order
                # Save the document

            # Exam

            if (no_bars_top == 3):
                cx1 = (1000 * clear_span - wall_thickness + nominal_cover + top_bar / 200)
                cx2 = ((
                        1000 * clear_span - wall_thickness + nominal_cover + top_bar / 200 + 1000 * clear_span - nominal_cover - top_bar / 200)) / 2
                cx3 = (1000 * clear_span - nominal_cover - top_bar / 200)
                cy1 = -4 * overall_depth - nominal_cover - top_bar / 200
                dot_centers = [(cx1, cy1), (cx2, cy1), (cx3, cy1)]  # Replace with the actual centers of the dots
                dot_radius = top_bar / 200
                top = 1
                create_dots_bb(dot_centers, dot_radius, top)

            elif (no_bars_top == 2):
                cx1 = (1000 * clear_span - wall_thickness + nominal_cover + top_bar / 200)
                cx3 = (1000 * clear_span - nominal_cover - top_bar / 200)
                cy1 = -4 * overall_depth - nominal_cover - top_bar / 200
                dot_centers = [(cx1, cy1), (cx3, cy1)]  # Replace with the actual centers of the dots
                dot_radius = top_bar / 200
                top = 1
                create_dots_bb(dot_centers, dot_radius, top)

            elif (no_bars_top == 4):
                cx1 = (1000 * clear_span - wall_thickness + nominal_cover + top_bar / 200)
                cx2 = (1000 * clear_span - wall_thickness + wall_thickness / 3 + top_bar / 200)
                cx3 = (1000 * clear_span - wall_thickness + 2 * wall_thickness / 3 - top_bar / 200)
                cx4 = (1000 * clear_span - nominal_cover - top_bar / 200)
                cy1 = -4 * overall_depth - nominal_cover - top_bar / 200
                dot_centers = [(cx1, cy1), (cx2, cy1), (cx3, cy1),
                               (cx4, cy1)]  # Replace with the actual centers of the dots
                dot_radius = top_bar / 200
                top = 1
                create_dots_bb(dot_centers, dot_radius, top)

            else:
                print("bars cannot be arranged")

            if (no_of_bars_bottom == 3):  # --------------------------------------------bottom
                x1 = (1000 * clear_span - wall_thickness + nominal_cover + main_bar / 200)
                x2 = ((
                        1000 * clear_span - wall_thickness + nominal_cover + main_bar / 200 + 1000 * clear_span - nominal_cover - main_bar / 200)) / 2
                x3 = (1000 * clear_span - nominal_cover - main_bar / 200)
                y2 = -5 * overall_depth + nominal_cover + main_bar / 200
                dot_centers1 = [(x1, y2), (x2, y2), (x3, y2)]  # Replace with the actual centers of the dots
                dot_radius1 = main_bar / 200
                bottom = 10
                create_dots_bb(dot_centers1, dot_radius1, bottom)
            elif (no_of_bars_bottom == 2):
                x1 = (1000 * clear_span - wall_thickness + nominal_cover + main_bar / 200)
                x3 = (1000 * clear_span - nominal_cover - main_bar / 200)
                y2 = -5 * overall_depth + nominal_cover + main_bar / 200
                dot_centers1 = [(x1, y2), (x3, y2)]  # Replace with the actual centers of the dots
                dot_radius1 = main_bar / 200
                bottom = 10
                create_dots_cc(dot_centers1, dot_radius1, bottom)
            elif (no_of_bars_bottom == 4):
                x1 = (1000 * clear_span - wall_thickness + nominal_cover + main_bar / 200)
                x2 = (1000 * clear_span - wall_thickness + wall_thickness / 3) + main_bar / 200
                x3 = (1000 * clear_span - wall_thickness + 2 * wall_thickness / 3) - main_bar / 200
                x4 = (1000 * clear_span - nominal_cover - main_bar / 200)
                y2 = -5 * overall_depth + nominal_cover + main_bar / 200
                dot_centers1 = [(x1, y2), (x2, y2), (x3, y2), (x4, y2)]  # Replace with the actual centers of the dots
                dot_radius1 = main_bar / 200
                bottom = 10
                create_dots_cc(dot_centers1, dot_radius1, bottom)
            else:
                print("bars cannot be arranged")

            dim.render()

            # Save the document as a DXF file
            file = "Cantilever.dxf"
            doc.saveas(file)
            print("Drwaing is created for Cantilever beam as:", file)
            print("bootom", no_of_bars_bottom)
            print("top", no_of_bars_top)

    # --------------------------------------------------------------------------------------------------------------simply--------------------------
    elif (beam_type == "Simply Supported"):  # ----------------------------------------------simply supported-----------------------
        beam_length = float(request.form['beam_length'])
        clear_span = beam_length
        exposure_condition = request.form['exposure']
        wall_thickness = float(request.form['wall_thickness'])
        fck = int(request.form['fck'])
        fy = int(request.form['fy'])
        live_load = float(request.form['udl'])
        num_point_loads = 0
        point_loads = []

        # Loop to get details for each point load
        for i in range(num_point_loads):
            magnitude = float(input(f"Enter the magnitude of point load #{i + 1} (in Kilo Newtons): ") or 50)
            position = float(input(f"Enter the position of point load #{i + 1} from one end (in meters): ") or 1.66)

            point_loads.append((magnitude, position))

        # You can now use `point_loads` for calculations in the rest of your script
        print("Point Loads:", point_loads)
        min_bar_dia = 8
        max_bar_dia = 20
        no_of_bars_bottom = None
        no_of_bars_top = None
        main_bar = None
        top_bar = None
        stdia = None

        def calculate_fsmpa(eps):
            if eps > 0.0038:
                return 360.9
            elif eps > 0.00276:
                return 351.8 + 9.1 / 0.00104 * (eps - 0.00276)
            elif eps > 0.00241:
                return 342.8 + 9 / 0.00035 * (eps - 0.00241)
            elif eps > 0.00192:
                return 324.8 + 18 / 0.00049 * (eps - 0.00192)
            elif eps > 0.00163:
                return 306.7 + 18.1 / 0.00029 * (eps - 0.00163)
            elif eps > 0.00144:
                return 288.7 + 18 / 0.00019 * (eps - 0.00144)
            else:
                return eps * 200000

        def get_effective_depth(clear_span, wall_thickness, exposure_condition, min_bar_dia, max_bar_dia):
            l = clear_span * 1000 + wall_thickness  # effective span in mm
            if (clear_span < 10):
                spanratio = 15
            else:
                spanratio = 20 * 10 / clear_span
            d = l / spanratio  # Assuming the span/depth ratio is 15
            nominal_cover = get_nominal_cover(exposure_condition)
            print(d)
            effective_cover = nominal_cover + min_bar_dia + (max_bar_dia / 2)
            print("effective cover: ", effective_cover)
            overall_depth = round(d + effective_cover, -2)
            effective_depth = overall_depth - effective_cover
            return effective_depth, overall_depth, l, effective_cover, nominal_cover

        def get_nominal_cover(exposure_condition):
            covers = {
                "Mild": 20,
                "Moderate": 30,
                "Severe": 45,
                "Very severe": 50,
                "Extreme": 75
            }
            return covers.get(exposure_condition, "Exposure not found")

        def get_tcmax(concrete_grade):
            # Dictionary containing the tcmax values for different concrete grades
            tcmax_values = {
                15: 2.5,
                20: 2.8,
                25: 3.1,
                30: 3.5,
                35: 3.7,
                40: 4.0
            }

            # Return the tcmax value for the given concrete grade
            return tcmax_values.get(concrete_grade, "Grade not found")

        # this would be user input in practice
        tcmax = get_tcmax(fck)

        # Calculate effective depth based on the provided parameters
        effective_depth, overall_depth, l, effective_cover, nominal_cover = get_effective_depth(clear_span,
                                                                                                wall_thickness,
                                                                                                exposure_condition,
                                                                                                min_bar_dia,
                                                                                                max_bar_dia)
        b = wall_thickness
        o_d = round(overall_depth, -2)
        print("Overall depth:", o_d)
        print("effective_depth: ", effective_depth)
        print("Assumed width of beam:", b)
        L = clear_span + wall_thickness / 1000  # Length of the beam (meters)
        # (Magnitude of the point load (Newtons), Position (meters from one end))
        q = live_load + wall_thickness * overall_depth * 25 / 1000000  # Magnitude of the uniform distributed load (Newtons per meter)
        s1 = 60 * wall_thickness
        s2 = 250 * wall_thickness * wall_thickness / effective_depth
        slender = min(s1, s2)
        if (clear_span > slender / 1000):
            return ("The clear distance between the lateral restraiant shall not exceeds 60 b or (250 b^2)/d which ever is less IS:456 Clause 23.3")
            sys.exit()
        # print(q)
        # Adjust calculation for support reactions
        def calculate_reactions(L, point_loads, q):
            moment_about_A = sum(P * a for P, a in point_loads) + (q * L ** 2) / 2
            Rb = moment_about_A / L  # Reaction at support B (right end)
            # print(moment_about_A)
            Ra = (q * L) + sum(P for P, _ in point_loads) - Rb
            # print(Ra,Rb)# Reaction at support A (left end)
            return Ra, Rb

        # Adjust shear force calculation
        def shear_force(x, L, point_loads, q, Ra):
            V = Ra - q * x
            for P, a in point_loads:
                if x >= a:
                    V -= P
            return V

        # Adjust bending moment calculation
        def bending_moment(x, L, point_loads, q, Ra):
            M = Ra * x - (q * x ** 2) / 2
            for P, a in point_loads:
                if x >= a:
                    M -= P * (x - a)
            return M

        Ra, Rb = calculate_reactions(L, point_loads, q)
        x_values = np.linspace(0, L, 500)
        shear_values = [shear_force(x, L, point_loads, q, Ra) for x in x_values]
        moment_values = [bending_moment(x, L, point_loads, q, Ra) for x in x_values]

        # Identifying maximum shear force and bending moment
        max_shear_force = max(abs(np.array(shear_values)))
        max_shear_force_position = x_values[np.argmax(np.abs(shear_values))]
        max_bending_moment = max(abs(np.array(moment_values)))
        max_bending_moment_position = x_values[np.argmax(np.abs(moment_values))]

        # Plot shear force and bending moment diagrams with adjustments for multiple point loads
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 10))

        # Shear Force Diagram
        ax1.plot(x_values, shear_values, label='Shear Force Diagram')
        ax1.axhline(y=0, color='k', linestyle='--')
        ax1.set_xlabel('Length of the beam (meters)')
        ax1.set_ylabel('Shear Force (kN)')
        ax1.set_ylim(min(shear_values) * 1.1, max(shear_values) * 1.1)
        ax1.legend()
        ax1.grid(True)

        # Bending Moment Diagram
        ax2.plot(x_values, moment_values, label='Bending Moment Diagram')
        ax2.axhline(y=0, color='k', linestyle='--')
        ax2.set_xlabel('Length of the beam (meters)')
        ax2.set_ylabel('Bending Moment (kN*m)')
        ax2.set_ylim(min(moment_values) * 1.1, max(moment_values) * 1.1)
        ax2.legend()
        ax2.grid(True)

        # Corrected annotations with proper facecolor specification
        ax1.annotate(f'Max Shear Force: {max_shear_force:.2f} kN\nPosition: {max_shear_force_position:.2f} m',
                     xy=(max_shear_force_position, 0), xytext=(max_shear_force_position + 0.5, max_shear_force * 0.5),
                     arrowprops=dict(facecolor='black', shrink=0.05),
                     bbox=dict(boxstyle='round,pad=0.2', fc='yellow', alpha=0.9), fontsize=10)

        ax2.annotate(f'Max Bending Moment: {max_bending_moment:.2f} kNm\nPosition: {max_bending_moment_position:.2f} m',
                     xy=(max_bending_moment_position, max_bending_moment),
                     xytext=(max_bending_moment_position - 3, max_bending_moment - 100),
                     arrowprops=dict(facecolor='black', shrink=0.05),
                     bbox=dict(boxstyle='round,pad=0.2', fc='yellow', alpha=0.9), fontsize=10)
        plt.tight_layout()
        plt.show()
        max_bending_moment = max_bending_moment
        print("Maximum bending moment:", max_bending_moment, "kN/m")
        ultimate_bending_moment = 1.5 * max_bending_moment
        print("Ultimate bending moment:", ultimate_bending_moment, "kN/m")
        max_shear_force = max_shear_force
        print("Max shear force:", max_shear_force, "kN")
        ultimate_shear_force = 1.5 * max_shear_force
        print("Ultimate shear force:", ultimate_shear_force, "kN")

        # step:3Check for Adequacy
        def get_xumax(fy):
            # Define the values based on the table provided
            xumax_values = {
                250: 0.53,
                415: 0.48,
                500: 0.46
            }

            # Return the Xumax value for the given fy
            return xumax_values.get(fy, "Grade of steel not found")

        # Call the function with fy=415
        xumax = get_xumax(fy)
        Ml = 0.36 * (xumax) * (1 - 0.42 * xumax) * b * effective_depth * effective_depth * fck

        ml = Ml / 1000000
        print("Mulimit :", ml, "kNm")
        # print(ml)
        mu = ultimate_bending_moment
        if (mu < ml):
            print("ultimate bending moment is less that Mulimt,so the section is under reinforced")
            # Step 4:Calculation of area of steel
            ast = 0.00574712643678161 * (
                    87 * b * effective_depth * fck -
                    9.32737905308882 * (b * fck * (
                    -400 * ultimate_bending_moment * 1000000 + 87 * b * effective_depth ** 2 * fck)) ** 0.5
            ) / fy
            print("ast", ast)
            astmin = 0.85 * b * effective_depth / fy
            print("astmin", astmin)
            astmax = .04 * b * o_d
            print("Maximum Ast:", astmax)
            if (astmax < astmin or astmax < ast):
                return("Revise Section,Tensile Reinforcement Exceeds 4%")
                sys.exit()
            # bottom bars
            if (ast > astmin):
                print("Ast will be governing for steel arrangement")
                main_bar = [12, 16, 20, 25, 32, 40]
                results = []
                for num in main_bar:
                    # Calculate the result
                    result = max(ast / (num * num * .785), 2)
                    results.append((num, math.ceil(result)))

                # Find suitable bar and count
                suitable_bars = [(num, count) for num, count in results if 2 <= count < 5]
                if suitable_bars:
                    main_bar, no_of_bars_bottom = suitable_bars[0]  # Select the first suitable option
                else:
                    main_bar, no_of_bars_bottom = (0, 0)  # Default to zero if no suitable option is found

                # Calculate the area of steel provided and percentage
                ab = no_of_bars_bottom * 0.78539816339744830961566084581988 * main_bar ** 2
                pt = 100 * ab / (b * effective_depth)

                # print(main_bar, no_of_bars, pt)
                main_bar_provided = main_bar
                # no_of_bars = round(ast / (0.78539816339744830961566084581988 * main_bar ** 2), 0)
                print("Provide", no_of_bars_bottom, "-Φ", main_bar, " mm as main bars at the bottom")
                # ab = no_of_bars * 0.78539816339744830961566084581988 * main_bar ** 2
                # pt = 100 * ab / (b * effective_depth)
                print("Percentage of steel provided(Tensile Reinforcement): ", pt)
            else:
                main_bar = [12, 16, 20, 25, 32, 40]
                results = []
                for num in main_bar:
                    # Calculate the result
                    result = max(astmin / (num * num * .785), 2)
                    results.append((num, math.ceil(result)))

                # Find suitable bar and count
                suitable_bars = [(num, count) for num, count in results if 2 <= count < 5]
                if suitable_bars:
                    main_bar, no_of_bars_bottom = suitable_bars[0]  # Select the first suitable option
                else:
                    main_bar, no_of_bars_bottom = (0, 0)  # Default to zero if no suitable option is found

                # Calculate the area of steel provided and percentage
                ab = no_of_bars_bottom * 0.78539816339744830961566084581988 * main_bar ** 2
                pt = 100 * ab / (b * effective_depth)

                # print(main_bar, no_of_bars, pt)
                main_bar_provided = main_bar
                # no_of_bars = round(ast / (0.78539816339744830961566084581988 * main_bar ** 2), 0)
                print("Provide", no_of_bars_bottom, "-Φ", main_bar, " mm as main bars at the bottom")
                # ab = no_of_bars * 0.78539816339744830961566084581988 * main_bar ** 2
                # pt = 100 * ab / (b * effective_depth)
                print("Percentage of steel provided(Tensile Reinforcement): ", pt)

                # top bars
            top_bar = [12, 16, 20, 25, 32, 40]
            results1 = []
            for num in top_bar:
                # Calculate the result
                result1 = max(astmin / (num * num * .785), 2)
                results1.append((num, math.ceil(result1)))

            # Find suitable bar and count
            suitable_bars = [(num, count) for num, count in results1 if 2 <= count < 5]
            if suitable_bars:
                top_bar, no_of_bars_top = suitable_bars[0]  # Select the first suitable option
            else:
                top_bar, no_of_bars_top = (0, 0)  # Default to zero if no suitable option is found
            if (no_of_bars_top == 0):
                no_of_bars_top = 2
                top_bar = 12

            # Calculate the area of steel provided and percentage
            ab = no_of_bars_top * 0.78539816339744830961566084581988 * top_bar ** 2
            pt = 100 * ab / (b * effective_depth)
            # print(main_bar, no_of_bars, pt)
            top_bar_provided = top_bar
            # no_of_bars = round(ast / (0.78539816339744830961566084581988 * main_bar ** 2), 0)
            print("Provide", no_of_bars_top, "-Φ", top_bar, " mm as main bars at the top")

            print("Percentage of steel provided(Compression Reinforcement): ", pt)
            #Side-face Reinforcement
            if o_d > 750:
                sideast = 0.0005 * wall_thickness * o_d
                side_bar = [12, 16, 20, 25, 32, 40]
                results1 = []
                print(sideast)
                # Calculate the required number of bars for each available diameter
                for num in side_bar:
                    # Calculate the result
                    required_area_per_bar = max(sideast / (num * num * 0.785), 2)
                    # Store the diameter and the required number of bars (rounded up)
                    results1.append((num, math.ceil(required_area_per_bar)))

                # Find suitable bars and count
                suitable_bars = [(num, count) for num, count in results1 if 1 <= count < 5]
                if suitable_bars:
                    side_bar, no_of_bars_side = suitable_bars[0]  # Select the first suitable option
                else:
                    side_bar, no_of_bars_side = (12, 1)  # Default to 12mm bar and 1 bar if no suitable option is found

                # Print the result
                print("Provide", no_of_bars_side, "no of", side_bar, "mm bars on each side of the beam")
            # step-5:check for shear
            vu = ultimate_shear_force * 1000
            tv = vu / (b * effective_depth)
            print(effective_depth)
            p = 100 * ast / (b * effective_depth)
            # print(p)

            beta = 0.8 * fck / (6.89 * p)
            f = (0.8 * fck) ** 0.5
            brta = ((1 + 5 * beta) ** 0.5) - 1
            tc = 0.85 * f * brta / (6 * beta)
            # tc=(0.85*((0.8*fck)**0.5)*((1+5*beta)**0.5)-1)/(6*beta)
            print("tc value: ", tc)
            print("tv value: ", tv)
            if (tv > tc and tv <= tcmax):
                Vus = ultimate_shear_force * 1000 - (tc * b * effective_depth)
                print("Vus value: ", Vus)
                stdia = 8
                leg = 2

                sv = 0.87 * fy * effective_depth * leg * 0.78539816339744830961566084581988 * stdia ** 2 / Vus
                spacing = min(0.75 * effective_depth, 300)
                max_spacing = (spacing // 25) * 25
                # print(max_spacing)
                print("Provide Φ", stdia, "- mm ", leg, "vertical stirrups @", max_spacing, "c/c")
            elif (tv <= tc):
                stdia = 8
                leg = 2

                sv = 0.87 * fy * leg * 0.78539816339744830961566084581988 * stdia ** 2 / (0.4 * wall_thickness)
                spacing = min(0.75 * effective_depth, 300)
                max_spacing = (spacing // 25) * 25
                print("spacing",spacing)
                print("Provide Φ", stdia, "- mm ", leg, "vertical stirrups @", max_spacing, "c/c")
            else:
                return("revise section (per Cl. 40.2.3, IS 456: 2000, pp. 72")
            # step 6:Check for Deflection
            Actualspan = l / effective_depth
            bd = b * effective_depth / (100 * ast)
            fs = 0.58 * fy
            mf = 1 / (0.225 + 0.003228 * fs - 0.625 * math.log10(bd))
            allowablespan = 20 * mf
            b1 = b  # width of the beam
            d1 = o_d  # overall_depth
            fck1 = fck
            span1 = clear_span
            m1 = max(mu, ml)
            creep = 1.6
            live_load1 = live_load
            perudl = live_load1 / 2
            cover1 = effective_cover
            effective_depth1 = effective_depth
            pc1 = 100 * no_of_bars_top * 0.78539816339744830961566084581988 * top_bar ** 2 / (b * effective_depth)
            astc = pc1 * b1 * d1 / 100
            pt1 = 100 * no_of_bars_bottom * 0.78539816339744830961566084581988 * main_bar ** 2 / (b * effective_depth)
            astt = pt1 * b1 * d1 / 100
            fcr = .7 * fck1 ** 0.5
            ig = (b1 * (d1 ** 3)) / 12
            mr = fcr * ig * 2 / d1 / 1000000
            ec = 5000 * fck1 ** .5
            short_m = 200000 / ec
            term1 = -(astc * (short_m - 1) + short_m * astt)
            term2 = (short_m - 1) ** 2 * astc ** 2 + short_m ** 2 * astt ** 2 + 2 * short_m * (
                    short_m - 1) * astc * astt
            term3 = 2 * b1 * ((short_m - 1) * astc * effective_cover + short_m * astt * effective_depth)
            sqrt_term = math.sqrt(term2 + term3)
            short_term_deflection = (term1 + sqrt_term) / b1
            t1 = b1 * (short_term_deflection ** 3) / 3
            t2 = short_m * astt * (effective_depth - short_term_deflection) ** 2
            t3 = (short_m - 1) * astc * (short_term_deflection - effective_cover) ** 2
            lr = t1 + t2 + t3
            lreff = lr / (1.2 - mr / m1 * (1 - short_term_deflection / d1 / 3) * (1 - short_term_deflection / d1))
            luse = max(lr, lreff)
            # longterm
            if (pt1 - pc1 < 1):
                k4 = .72 * (pt1 - pc1) / math.sqrt(pt1)
            else:
                k4 = .65 * (pt1 - pc1) / math.sqrt(pt1)

            ecc = ec / (creep + 1)
            mc = 200000 / ecc
            terml1 = -(astc * (mc - 1) + mc * astt)
            terml2 = (mc - 1) ** 2 * astc ** 2 + mc ** 2 * astt ** 2 + 2 * mc * (mc - 1) * astc * astt
            terml3 = 2 * b1 * ((mc - 1) * astc * effective_cover + mc * astt * effective_depth)
            sqrt_term1 = math.sqrt(terml2 + terml3)
            long_term_deflection = (terml1 + sqrt_term1) / b1
            tl1 = b1 * (long_term_deflection ** 3) / 3
            tl2 = mc * astt * (effective_depth - long_term_deflection) ** 2
            tl3 = (mc - 1) * astc * (long_term_deflection - effective_cover) ** 2
            lrc = tl1 + tl2 + tl3
            lceff = lrc / (1.2 - mc / m1 * (1 - long_term_deflection / d1 / 3) * (1 - long_term_deflection / d1))
            if lceff < lrc:
                leffuse = lrc if lrc < ig else ig
            else:
                leffuse = lceff if lceff < ig else ig
            aicc = 5 / 384 * perudl * (clear_span ** 4) * 1000000000000 / (ecc) / leffuse
            print("aicc",aicc)
            ai = 5 / 384 * perudl * (clear_span ** 4) * 1000000000000 / (ec) / luse
            print("ai",ai)
            short_term_delta = 5 / 384 * live_load1 * (clear_span ** 4) * 1000000000000 / (ec) / luse
            shrinkage = 0.0003 * k4 / d1 * .125 * clear_span * clear_span * 1000000
            print("k4",k4)
            print("sd",short_term_delta)
            creep_x = abs(aicc - ai)
            long_term_delta = creep_x + shrinkage
            total_deflection = long_term_delta + short_term_delta
            delta_allowable = clear_span * 1000 / 250
            span_ltd = clear_span * 1000 / (creep_x + shrinkage)
            print("creep",creep_x)
            print("shrinkage",shrinkage)
            span_net = clear_span * 1000 / (total_deflection)
            if (long_term_delta > 20):
                return("Revise Section,Long Term Deflection Exceeds 20mm")
                sys.exit()
            elif (span_ltd < 350):
                print(span_ltd)
                return("Revise Section,span/Long Term Deflection is less than 350")
                sys.exit()
            elif (span_net < 250):
                print(span_net)
                return("Revise Section,span/Net Total Term Deflection is less than 250")
                sys.exit()
            print("modification factor: ", mf)
            if (allowablespan > Actualspan):
                print(" The section is safe under deflection")
            else:
                return(" revise section")



        else:
            print("the section is over reinforced")
            ast1 = 0.00574712643678161 * (
                    87 * b * effective_depth * fck -
                    9.32737905308882 * (b * fck * (-400 * Ml + 87 * b * effective_depth ** 2 * fck)) ** 0.5
            ) / fy
            mu = ultimate_bending_moment
            ast2 = (mu - ml) * 10 ** 6 / (0.87 * fy * (effective_depth - effective_cover))
            ast = ast2 + ast1
            ast2 = (mu - ml) * 10 ** 6 / (0.87 * fy * (effective_depth - effective_cover))
            astmin = 0.85 * b * effective_depth / fy
            astmax = .04 * b * (effective_depth + effective_cover)
            print("Maximum Ast:", astmax)
            if (astmax < astmin or astmax < ast):
                return("Revise Section,Tensile Reinforcement Exceeds 4%")
                sys.exit()
            # print(ast)
            # print(ast2)
            # print(ast1)
            main_bar = [12, 16, 20, 25, 32, 40]
            results = []
            for num in main_bar:
                # Calculate the result
                result = ast / (num * num * .785)
                results.append((num, math.ceil(result)))

            # Find suitable bar and count
            suitable_bars = [(num, count) for num, count in results if 2 <= count < 5]
            if suitable_bars:
                main_bar, no_of_bars_bottom = suitable_bars[0]  # Select the first suitable option
            else:
                main_bar, no_of_bars_bottom = (0, 0)  # Default to zero if no suitable option is found
                return("Revise Section,Bars are too close to each other")
                sys.exit()
            # Calculate the area of steel provided and percentage
            ab = no_of_bars_bottom * 0.78539816339744830961566084581988 * main_bar ** 2
            pt = 100 * ab / (b * effective_depth)
            # print(main_bar, no_of_bars, pt)
            main_bar_provided = main_bar
            print(f"provide {no_of_bars_bottom} - Φ {main_bar} mm as main bars at the bottom")
            print("percentage of steel provided(Tensile Reinforcement): ", pt)
            # compression steel
            ast2 = (mu - ml) * 10 ** 6 / (0.87 * fy * (effective_depth - effective_cover))
            astmin = 0.85 * b * effective_depth / fy

            if (astmin > ast2):
                top_bar = [12, 16, 20, 25, 32, 40]
                results1 = []
                for num in top_bar:
                    # Calculate the result
                    result1 = astmin / (num * num * .785)
                    results1.append((num, math.ceil(result1)))
                # Find suitable bar and count
                suitable_bars = [(num, count) for num, count in results1 if 2 <= count < 5]
                if suitable_bars:
                    top_bar, no_of_bars_top = suitable_bars[0]  # Select the first suitable option
                else:
                    top_bar, no_of_bars_top = (0, 0)  # Default to zero if no suitable option is found
                if (no_of_bars_top == 0):
                    no_of_bars_top = 2
                    top_bar = 12
                # Calculate the area of steel provided and percentage
                ab = no_of_bars_top * 0.78539816339744830961566084581988 * top_bar ** 2
                pt = 100 * ab / (b * effective_depth)
                # print(main_bar, no_of_bars, pt)
                top_bar_provided = top_bar
                print("provide", no_of_bars_top, "-Φ", top_bar, " mm as main bars at the top")

                print("percentage of steel provided(Compression Reinforcement): ", pt)
            else:
                top_bar = [12, 16, 20, 25, 32, 40]
                results1 = []
                for num in top_bar:
                    # Calculate the result
                    result1 = ast2 / (num * num * .785)
                    results1.append((num, math.ceil(result1)))
                # Find suitable bar and count
                suitable_bars = [(num, count) for num, count in results1 if 2 <= count < 5]
                if suitable_bars:
                    top_bar, no_of_bars_top = suitable_bars[0]  # Select the first suitable option
                else:
                    top_bar, no_of_bars_top = (0, 0)  # Default to zero if no suitable option is found
                if (no_of_bars_top == 0):
                    no_of_bars_top = 2
                    top_bar = 12
                # Calculate the area of steel provided and percentage
                ab = no_of_bars_top * 0.78539816339744830961566084581988 * top_bar ** 2
                pt = 100 * ab / (b * effective_depth)
                # print(main_bar, no_of_bars, pt)
                top_bar_provided = top_bar
                print("provide", no_of_bars_top, "-Φ", top_bar, " mm as main bars at the top")
                print("percentage of steel provided(Compression Reinforcement): ", pt)
            #side face
            if o_d > 750:
                sideast = 0.0005 * wall_thickness * o_d
                side_bar = [12, 16, 20, 25, 32, 40]
                results1 = []
                print(sideast)
                # Calculate the required number of bars for each available diameter
                for num in side_bar:
                    # Calculate the result
                    required_area_per_bar = max(sideast / (num * num * 0.785), 2)
                    # Store the diameter and the required number of bars (rounded up)
                    results1.append((num, math.ceil(required_area_per_bar)))

                # Find suitable bars and count
                suitable_bars = [(num, count) for num, count in results1 if 1 <= count < 5]
                if suitable_bars:
                    side_bar, no_of_bars_side = suitable_bars[0]  # Select the first suitable option
                else:
                    side_bar, no_of_bars_side = (12, 1)  # Default to 12mm bar and 1 bar if no suitable option is found

                # Print the result
                print("Provide", no_of_bars_side, "no of", side_bar, "mm bars on each side of the beam")
            # step-5:check for shear
            vu = ultimate_shear_force * 1000
            tv = vu / (b * effective_depth)
            # print(effective_depth)
            p = 100 * ast / (b * effective_depth)
            # print(p)

            beta = 0.8 * fck / (6.89 * p)
            f = (0.8 * fck) ** 0.5
            brta = ((1 + 5 * beta) ** 0.5) - 1
            tc = 0.85 * f * brta / (6 * beta)
            # tc=(0.85*((0.8*fck)**0.5)*((1+5*beta)**0.5)-1)/(6*beta)
            print("tc value: ", tc)
            print("tv value: ", tv)
            stdia = 8
            leg = 2
            if (tv > tc):
                Vus = ultimate_shear_force * 1000 - (tc * b * effective_depth)
                print("Vus value: ", Vus)
                # stdia = int(input("enter the diameter of the stirrup in mm: ") or 8)
                # leg = int(input("enter the number of legs for the stirrups: ") or 2)

                sv = 0.87 * fy * effective_depth * leg * 0.78539816339744830961566084581988 * stdia ** 2 / Vus
                spacing = min(0.75 * effective_depth, 300)
                max_spacing = (spacing // 25) * 25
                # print(max_spacing)
                print("Provide Φ", stdia, "- mm ", leg, "vertical stirrups @", max_spacing, "c/c")
            else:
                # stdia = int(input("enter the diameter of the stirrup in mm: ") or 8)
                # leg = int(input("enter the number of legs for the stirrups: ") or 2)
                sv = 0.87 * fy * leg * 0.78539816339744830961566084581988 * stdia ** 2 / (4 * wall_thickness)
                spacing = min(0.75 * effective_depth, 300)
                max_spacing = (spacing // 25) * 25
                # print(max_spacing)
                print("Provide Φ", stdia, "- mm ", leg, "vertical stirrups @", max_spacing, "c/c")
                # step 6:Check for Deflection
            Actualspan = l / effective_depth
            bd = b * effective_depth / (100 * ast)
            fs = 0.58 * fy

            mf = 1 / (0.225 + 0.003228 * fs - 0.625 * math.log10(bd))
            pc = ast1 * 100 / (b * effective_depth)
            multiplyingfactor = 1.6 * pc / (pc + 0.275)
            allowablespan = 20 * mf * multiplyingfactor
            print("multiplying factor : ", multiplyingfactor)
            print("modification factor: ", mf)
            b1 = b  # width of the beam
            d1 = o_d  # overall_depth
            fck1 = fck
            span1 = clear_span
            m1 = max(mu, ml)
            creep = 1.6
            live_load1 = live_load
            perudl = live_load1 / 2
            cover1 = effective_cover
            effective_depth1 = effective_depth
            pc1 = 100 * no_of_bars_top * 0.78539816339744830961566084581988 * top_bar ** 2 / (b * effective_depth)
            astc = pc1 * b1 * d1 / 100
            pt1 = 100 * no_of_bars_bottom * 0.78539816339744830961566084581988 * main_bar ** 2 / (b * effective_depth)
            astt = pt1 * b1 * d1 / 100
            fcr = .7 * fck1 ** 0.5
            ig = (b1 * (d1 ** 3)) / 12
            mr = fcr * ig * 2 / d1 / 1000000
            ec = 5000 * fck1 ** .5
            short_m = 200000 / ec
            term1 = -(astc * (short_m - 1) + short_m * astt)
            term2 = (short_m - 1) ** 2 * astc ** 2 + short_m ** 2 * astt ** 2 + 2 * short_m * (
                    short_m - 1) * astc * astt
            term3 = 2 * b1 * ((short_m - 1) * astc * effective_cover + short_m * astt * effective_depth)
            sqrt_term = math.sqrt(term2 + term3)
            short_term_deflection = (term1 + sqrt_term) / b1
            t1 = b1 * (short_term_deflection ** 3) / 3
            t2 = short_m * astt * (effective_depth - short_term_deflection) ** 2
            t3 = (short_m - 1) * astc * (short_term_deflection - effective_cover) ** 2
            lr = t1 + t2 + t3
            lreff = lr / (1.2 - mr / m1 * (1 - short_term_deflection / d1 / 3) * (1 - short_term_deflection / d1))
            luse = max(lr, lreff)
            # longterm
            if (pt1 - pc1 < 1):
                k4 = .72 * (pt1 - pc1) / math.sqrt(pt1)
            else:
                k4 = .65 * (pt1 - pc1) / math.sqrt(pt1)

            ecc = ec / (creep + 1)
            mc = 200000 / ecc
            terml1 = -(astc * (mc - 1) + mc * astt)
            terml2 = (mc - 1) ** 2 * astc ** 2 + mc ** 2 * astt ** 2 + 2 * mc * (mc - 1) * astc * astt
            terml3 = 2 * b1 * ((mc - 1) * astc * effective_cover + mc * astt * effective_depth)
            sqrt_term1 = math.sqrt(terml2 + terml3)
            long_term_deflection = (terml1 + sqrt_term1) / b1
            tl1 = b1 * (long_term_deflection ** 3) / 3
            tl2 = mc * astt * (effective_depth - long_term_deflection) ** 2
            tl3 = (mc - 1) * astc * (long_term_deflection - effective_cover) ** 2
            lrc = tl1 + tl2 + tl3
            lceff = lrc / (1.2 - mc / m1 * (1 - long_term_deflection / d1 / 3) * (1 - long_term_deflection / d1))
            if lceff < lrc:
                leffuse = lrc if lrc < ig else ig
            else:
                leffuse = lceff if lceff < ig else ig
            aicc = 5 / 384 * perudl * (clear_span ** 4) * 1000000000000 / (ecc) / leffuse
            ai = 5 / 384 * perudl * (clear_span ** 4) * 1000000000000 / (ec) / luse
            short_term_delta = 5 / 384 * live_load1 * (clear_span ** 4) * 1000000000000 / (ec) / luse
            shrinkage = 0.0003 * k4 / d1 * .125 * clear_span * clear_span * 1000000
            creep_x = aicc - ai
            long_term_delta = creep_x + shrinkage
            total_deflection = long_term_delta + short_term_delta
            delta_allowable = clear_span * 1000 / 250
            span_ltd = clear_span * 1000 / (creep_x + shrinkage)
            span_net = clear_span * 1000 / (total_deflection)
            if (long_term_delta > 20):
                return("Revise Section,Long Term Deflection Exceeds 20mm")
                sys.exit()
            elif (span_ltd < 350):
                return("Revise Section,span/Long Term Deflection is less than 350")
                sys.exit()
            elif (span_net < 250):
                return("Revise Section,span/Net Total Term Deflection is less than 250")
                sys.exit()
            # print("modification factor: ", mf)
            if (allowablespan > Actualspan):
                print(" The section is safe under deflection")
            else:
                return(" revise section")
        no_bars_bottom = no_of_bars_bottom
        no_bars_top = no_of_bars_top
        main_bar = main_bar
        top_bar = top_bar
        effective_cover = effective_cover
        stdia = stdia
        clear_span = clear_span / 100
        wall_thickness = wall_thickness / 100
        overall_depth = overall_depth / 100
        # Initiate DXF file and access model space
        doc = ezdxf.new(setup=True)
        msp = doc.modelspace()
        dimstyle = doc.dimstyles.new("MyCustomStyle")
        dimstyle.dxf.dimasz = 0.5
        dimstyle.dxf.dimtxt = .1
        # dimstyle.dxf.dim
        # which is a shortcut (including validation) for
        doc.header['$INSUNITS'] = units.MM

        x = -wall_thickness + nominal_cover / 100
        y = overall_depth - nominal_cover / 100
        x1 = clear_span * 1000 + wall_thickness - nominal_cover / 100
        x11 = clear_span * 100
        y1 = overall_depth - nominal_cover / 100
        x3 = -wall_thickness + nominal_cover / 100
        x31 = clear_span * 800
        y3 = nominal_cover / 100
        x4 = clear_span * 1000 + wall_thickness - nominal_cover / 100
        y4 = nominal_cover / 100
        x5 = -wall_thickness / 2
        y5 = overall_depth / 1.2
        x6 = clear_span * 1000 + 2 * wall_thickness / 4
        y6 = overall_depth / 1.2

        # Create a Line
        msp.add_line((x, y), (x1, y1))  # top bar
        msp.add_line((x3, y3), (x4, y4))  # bottom bar
        msp.add_line((0, 0), (clear_span * 1000 + wall_thickness, 0))
        msp.add_line((0, 0), (-wall_thickness, 0))
        msp.add_line((-wall_thickness, 0), (-wall_thickness, overall_depth))
        msp.add_line((-wall_thickness, overall_depth), (0, overall_depth))
        msp.add_line((-wall_thickness, 0), (-wall_thickness, -overall_depth))
        msp.add_line((-wall_thickness, -overall_depth), (0, -overall_depth))
        msp.add_line((0, -overall_depth), (0, 0))
        # msp.add_line((0,0),(0,overall_depth))
        msp.add_line((0, overall_depth), (clear_span * 1000 + wall_thickness, overall_depth))
        msp.add_line((clear_span * 1000 + wall_thickness, overall_depth), (clear_span * 1000 + wall_thickness, 0))
        msp.add_line((clear_span * 1000, 0), (clear_span * 1000, -overall_depth))
        msp.add_line((clear_span * 1000, -overall_depth), (clear_span * 1000 + wall_thickness, -overall_depth))
        msp.add_line((clear_span * 1000 + wall_thickness, -overall_depth),
                     (clear_span * 1000 + wall_thickness, overall_depth))
        msp.add_line((clear_span * 500, 0), (clear_span * 500, overall_depth))
        # cross-section
        msp.add_line((0, -5 * overall_depth), (wall_thickness, -5 * overall_depth))  # bottom line
        msp.add_line((0, -5 * overall_depth), (0, -4 * overall_depth))  # left line
        msp.add_line((0, -4 * overall_depth), (wall_thickness, -4 * overall_depth))
        msp.add_line((wall_thickness, -4 * overall_depth), (wall_thickness, -5 * overall_depth))
        # --stirrup cross
        nominal_cover = nominal_cover / 100
        msp.add_line((0 + nominal_cover, -5 * overall_depth + nominal_cover),
                     (wall_thickness - nominal_cover, -5 * overall_depth + nominal_cover))  # bottom line
        msp.add_line((0 + nominal_cover, -5 * overall_depth + nominal_cover),
                     (0 + nominal_cover, -4 * overall_depth - nominal_cover))  # left line
        msp.add_line((0 + nominal_cover, -4 * overall_depth - nominal_cover),
                     (wall_thickness - nominal_cover, -4 * overall_depth - nominal_cover))
        msp.add_line((wall_thickness - nominal_cover, -4 * overall_depth - nominal_cover),
                     (wall_thickness - nominal_cover, -5 * overall_depth + nominal_cover))
        ml_builder = msp.add_multileader_mtext("Standard")

        ct = "Provide", no_of_bars_bottom, "Φ", main_bar, "- mm as \n main bars at the bottom"
        content_str = ', '.join(map(str, ct))
        ml_builder.set_content(content_str, style="OpenSans", char_height=.7,
                               alignment=mleader.TextAlignment.center, )

        X22 = clear_span * 1000
        X11 = clear_span
        ml_builder.add_leader_line(mleader.ConnectionSide.left, [Vec2(X11, y4)])
        ml_builder.add_leader_line(mleader.ConnectionSide.right, [Vec2(X22, y4)])
        ml_builder.build(insert=Vec2(clear_span * 500, -1 * overall_depth))

        # -----top bar
        ml_builder1 = msp.add_multileader_mtext("Standard")
        content_str1 = "Provide", no_of_bars_top, "-Φ", top_bar, "- mm \n as main bars at the top"
        content_str1 = ', '.join(map(str, content_str1))
        ml_builder1.set_content(content_str1, style="OpenSans", char_height=.7,
                                alignment=mleader.TextAlignment.center, )
        X32 = clear_span
        X31 = clear_span * 1000
        ml_builder1.add_leader_line(mleader.ConnectionSide.right, [Vec2(X31, y1)])
        ml_builder1.add_leader_line(mleader.ConnectionSide.left, [Vec2(X32, y1)])
        ml_builder1.build(insert=Vec2(500 * clear_span, 1.5 * overall_depth))
        # ----striupp
        ml_builder2 = msp.add_multileader_mtext("Standard")
        content_str3 = "Provide Φ", stdia, " -mm", leg, "\n" " legged vertical stirrups @", max_spacing, "c/c"
        content_str3 = ', '.join(map(str, content_str3))
        ml_builder2.set_content(
            content_str3,
            style="OpenSans",
            char_height=1,
            alignment=mleader.TextAlignment.left,  # set MTEXT alignment!
        )
        X6 = clear_span * 1000
        Y6 = overall_depth
        ml_builder2.add_leader_line(mleader.ConnectionSide.left, [Vec2(X6 / 2, Y6 / 2)])
        ml_builder2.build(insert=Vec2(clear_span * 800, 3 * overall_depth))
        # dimensions
        # Adda horizontal linear DIMENSION entity:
        dimstyle = doc.dimstyles.get("EZDXF")
        dimstyle.dxf.dimtxt = 1
        dim = msp.add_linear_dim(
            base=(0, -2 * overall_depth),  # location of the dimension line
            p1=(0, 0),  # 1st measurement point
            p2=(clear_span * 1000, 0),  # 2nd measurement point
            dimstyle="EZDXF",  # default dimension style
        )
        dim1 = msp.add_linear_dim(
            base=(0, -2 * overall_depth),  # location of the dimension line
            p1=(-wall_thickness, -overall_depth),  # 1st measurement point
            p2=(0, -overall_depth),  # 2nd measurement point
            dimstyle="EZDXF",  # default dimension style
        )
        dim2 = msp.add_linear_dim(
            base=(0, -2 * overall_depth),  # location of the dimension line
            p1=(clear_span * 1000, 0),  # 1st measurement point
            p2=(clear_span * 1000 + wall_thickness, 0),  # 2nd measurement point
            dimstyle="EZDXF",  # default dimension style
        )
        # hatch
        hatch = msp.add_hatch()
        hatch.set_pattern_fill("ANSI32", scale=.1)
        hatch.paths.add_polyline_path(
            [(0, 0), (-wall_thickness, 0), (-wall_thickness, -overall_depth), (0, -overall_depth)], is_closed=True
        )
        hatch1 = msp.add_hatch()
        hatch1.set_pattern_fill("ANSI32", scale=.1)
        hatch1.paths.add_polyline_path(
            [(clear_span * 1000, 0), (clear_span * 1000 + wall_thickness, 0),
             (clear_span * 1000 + wall_thickness, -overall_depth), (clear_span * 1000, -overall_depth)], is_closed=True
        )

        def create_dots(dot_centers, dot_radius, top):
            # Create a new DXF document

            # Create solid dots at specified centers with given radius
            for center in dot_centers:
                # Create a HATCH entity with a solid fill
                hatch = msp.add_hatch()
                # Add a circular path to the hatch as its boundary
                edge_path = hatch.paths.add_edge_path()
                edge_path.add_arc(center=center, radius=dot_radius, start_angle=0, end_angle=360)
                # Set the hatch pattern to solid
                hatch.set_solid_fill()
                if (top == 1):
                    msp.add_diameter_dim(
                        center=center,
                        radius=dot_radius,
                        # text=None,
                        dimstyle="EZ_RADIUS",
                        angle=135,  # Adjust the angle as needed
                        override={'dimtad': 0, 'dimasz': .2, 'dimexo': 5000, "dimtoh": 1, "dimlfac": 100},
                        # 16MM # Moves dimension line outside if it overlaps with the circle
                        dxfattribs={'layer': 'dimensions'}
                    ).render()
                else:
                    msp.add_diameter_dim(
                        center=center,
                        radius=dot_radius,
                        dimstyle="EZ_RADIUS",
                        angle=135,  # Adjust the angle as needed
                        override={'dimtad': 0, 'dimasz': .2, 'dimexo': 5000, "dimtoh": 1, "dimlfac": 100},
                        # 12MM  # Moves dimension line outside if it overlaps with the circle
                        dxfattribs={'layer': 'dimensions'}
                    ).render()

            # Create a rectangle from the provided corners
            # Assuming rectangle_corners is a list of tuples [(x1, y1), (x2, y2), (x3, y3), (x4, y4)] in consecutive order
            # Save the document

        # Exam

        if (no_bars_top == 3):
            cx1 = (0 + nominal_cover + top_bar / 200)
            cx2 = ((0 + nominal_cover + top_bar / 200 + 0 + wall_thickness - nominal_cover - top_bar / 200)) / 2
            cx3 = (0 + wall_thickness - nominal_cover - top_bar / 200)
            cy1 = -4 * overall_depth - nominal_cover - top_bar / 200
            dot_centers = [(cx1, cy1), (cx2, cy1), (cx3, cy1)]  # Replace with the actual centers of the dots
            dot_radius = top_bar / 200
            top = 1
            create_dots(dot_centers, dot_radius, top)

        elif (no_bars_top == 2):
            cx1 = (0 + nominal_cover + top_bar / 200)
            cx3 = (0 + wall_thickness - nominal_cover - top_bar / 200)
            cy1 = -4 * overall_depth - nominal_cover - top_bar / 200
            dot_centers = [(cx1, cy1), (cx3, cy1)]  # Replace with the actual centers of the dots
            dot_radius = top_bar / 200
            top = 1
            create_dots(dot_centers, dot_radius, top)

        elif (no_bars_top == 4):
            cx1 = (0 + nominal_cover + top_bar / 200)
            cx2 = (wall_thickness - nominal_cover * 2) / 3 + nominal_cover
            cx3 = 2 * (wall_thickness - nominal_cover * 2) / 3 + nominal_cover
            cx4 = (0 + wall_thickness - nominal_cover - top_bar / 200)
            cy1 = -4 * overall_depth - nominal_cover - top_bar / 200
            dot_centers = [(cx1, cy1), (cx2, cy1), (cx3, cy1),
                           (cx4, cy1)]  # Replace with the actual centers of the dots
            dot_radius = top_bar / 200
            top = 1
            create_dots(dot_centers, dot_radius, top)

        else:
            print("bars cannot be arranged")

        if (no_of_bars_bottom == 3):  # --------------------------------------------bottom
            x1 = (0 + nominal_cover + main_bar / 200)
            x2 = ((0 + nominal_cover + main_bar / 200 + 0 + wall_thickness - nominal_cover - main_bar / 200)) / 2
            x3 = (0 + wall_thickness - nominal_cover - main_bar / 200)
            y2 = -5 * overall_depth + nominal_cover + main_bar / 200
            dot_centers1 = [(x1, y2), (x2, y2), (x3, y2)]  # Replace with the actual centers of the dots
            dot_radius1 = main_bar / 200
            bottom = 10
            create_dots(dot_centers1, dot_radius1, bottom)
        elif (no_of_bars_bottom == 2):
            x1 = (0 + nominal_cover + main_bar / 200)
            x3 = (0 + wall_thickness - nominal_cover - main_bar / 200)
            y2 = -5 * overall_depth + nominal_cover + main_bar / 200
            dot_centers1 = [(x1, y2), (x3, y2)]  # Replace with the actual centers of the dots
            dot_radius1 = main_bar / 200
            bottom = 10
            create_dots(dot_centers1, dot_radius1, bottom)
        elif (no_of_bars_bottom == 4):
            x1 = (0 + nominal_cover + main_bar / 200)
            x2 = (wall_thickness - nominal_cover * 2) / 3 + nominal_cover
            x3 = 2 * (wall_thickness - nominal_cover * 2) / 3 + nominal_cover
            x4 = (0 + wall_thickness - nominal_cover - main_bar / 200)
            y2 = -5 * overall_depth + nominal_cover + main_bar / 200
            dot_centers1 = [(x1, y2), (x2, y2), (x3, y2), (x4, y2)]  # Replace with the actual centers of the dots
            dot_radius1 = main_bar / 200
            bottom = 10
            create_dots(dot_centers1, dot_radius1, bottom)
        else:
            print("bars cannot be arranged")

        # cross section dimension
        dim3 = msp.add_linear_dim(
            base=(0, -5.5 * overall_depth),  # location of the dimension line
            p1=(0, -4 * overall_depth),  # 1st measurement point
            p2=(wall_thickness, -4 * overall_depth),  # 2nd measurement point
            dimstyle="EZDXF",  # default dimension style
        )
        msp.add_linear_dim(base=(-1 * wall_thickness, -3.5 * overall_depth), p1=(0, -4 * overall_depth),
                           p2=(0, -5 * overall_depth), angle=90).render()  # cross section
        # msp.add_linear_dim(base=(1.1*clear_span*1000, overall_depth/2), p1=(1.2*clear_span*1000, 0), p2=(1.2*clear_span*1000, overall_depth), angle=90).render()
        msp.add_linear_dim(base=(-2 * wall_thickness, overall_depth / 2), p1=(-wall_thickness, 0),
                           p2=(-wall_thickness, overall_depth), angle=90).render()  # overall depth dim

        text_string = "LONGITUDINAL SECTION (all units are in mm)"
        insert_point = (100 * clear_span, -3 * overall_depth)  # X, Y coordinates where the text will be inserted.
        text_height = 1  # Height of the text.

        # Add text to the modelspace.
        msp.add_text(
            text_string,
            dxfattribs={
                'insert': insert_point,
                'height': text_height,
                # Additional attributes such as font, rotation, and color can be specified here.
                'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                'rotation': 0,
                'color': 7
            }
        )

        text_string = "SECTION A-A"
        insert_point = (-wall_thickness, -7 * overall_depth)  # X, Y coordinates where the text will be inserted.
        text_height = 1
        # Add text to the modelspace.
        msp.add_text(
            text_string,
            dxfattribs={
                'insert': insert_point,
                'height': text_height,
                # Additional attributes such as font, rotation, and color can be specified here.
                'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                'rotation': 0,
                'color': 7
            }
        )
        text_string = "SECTION B-B"
        insert_point = (400 * clear_span, -7 * overall_depth)  # X, Y coordinates where the text will be inserted.
        text_height = 1
        # Add text to the modelspace.
        msp.add_text(
            text_string,
            dxfattribs={
                'insert': insert_point,
                'height': text_height,
                # Additional attributes such as font, rotation, and color can be specified here.
                'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                'rotation': 0,
                'color': 7
            }
        )
        # section b-b
        msp.add_line((500 * clear_span, -5 * overall_depth),
                     (500 * clear_span - wall_thickness, -5 * overall_depth))  # bottom line
        msp.add_line((500 * clear_span - wall_thickness, -5 * overall_depth),
                     (500 * clear_span - wall_thickness, -4 * overall_depth))  # left line
        msp.add_line((500 * clear_span - wall_thickness, -4 * overall_depth), (500 * clear_span, -4 * overall_depth))
        msp.add_line((500 * clear_span, -4 * overall_depth), (500 * clear_span, -5 * overall_depth))
        # --stirrup cross
        nominal_cover = nominal_cover
        msp.add_line((500 * clear_span - nominal_cover, -5 * overall_depth + nominal_cover),
                     (500 * clear_span - wall_thickness + nominal_cover,
                      -5 * overall_depth + nominal_cover))  # bottom line
        msp.add_line((500 * clear_span - wall_thickness + nominal_cover, -5 * overall_depth + nominal_cover),
                     (500 * clear_span - wall_thickness + nominal_cover,
                      -4 * overall_depth - nominal_cover))  # left line
        msp.add_line((500 * clear_span - wall_thickness + nominal_cover, -4 * overall_depth - nominal_cover),
                     (500 * clear_span - nominal_cover, -4 * overall_depth - nominal_cover))
        msp.add_line((500 * clear_span - nominal_cover, -4 * overall_depth - nominal_cover),
                     (500 * clear_span - nominal_cover, -5 * overall_depth + nominal_cover))

        # cross section dimension
        dim3 = msp.add_linear_dim(
            base=(400 * clear_span, -5.5 * overall_depth),  # location of the dimension line
            p1=(500 * clear_span, -5 * overall_depth),  # 1st measurement point
            p2=(500 * clear_span - wall_thickness, -5 * overall_depth),  # 2nd measurement point
            dimstyle="EZDXF",  # default dimension style
        )
        msp.add_linear_dim(base=(400 * clear_span, -3.5 * overall_depth),
                           p1=(500 * clear_span - wall_thickness, -5 * overall_depth),
                           p2=(500 * clear_span - wall_thickness, -4 * overall_depth),
                           angle=90).render()  # cross section

        def create_dots_bb(dot_centers, dot_radius, top):
            # Create solid dots at specified centers with given radius
            for center in dot_centers:
                # Create a HATCH entity with a solid fill
                hatch = msp.add_hatch()
                # Add a circular path to the hatch as its boundary
                edge_path = hatch.paths.add_edge_path()
                edge_path.add_arc(center=center, radius=dot_radius, start_angle=0, end_angle=360)
                # Set the hatch pattern to solid
                hatch.set_solid_fill()
                if (top == 1):
                    msp.add_diameter_dim(
                        center=center,
                        radius=dot_radius,
                        # text=None,
                        dimstyle="EZ_RADIUS",
                        angle=135,  # Adjust the angle as needed
                        override={'dimtad': 0, 'dimasz': .2, 'dimexo': 5000, "dimtoh": 1, "dimlfac": 100},
                        # 16MM # Moves dimension line outside if it overlaps with the circle
                        dxfattribs={'layer': 'dimensions'}
                    ).render()
                else:
                    msp.add_diameter_dim(
                        center=center,
                        radius=dot_radius,
                        dimstyle="EZ_RADIUS",
                        angle=135,  # Adjust the angle as needed
                        override={'dimtad': 0, 'dimasz': .2, 'dimexo': 5000, "dimtoh": 1, "dimlfac": 100},
                        # 12MM  # Moves dimension line outside if it overlaps with the circle
                        dxfattribs={'layer': 'dimensions'}
                    ).render()

            # Create a rectangle from the provided corners
            # Assuming rectangle_corners is a list of tuples [(x1, y1), (x2, y2), (x3, y3), (x4, y4)] in consecutive order
            # Save the document

        # Exam

        if (no_bars_top == 3):
            cx1 = (500 * clear_span - wall_thickness + nominal_cover + top_bar / 200)
            cx2 = ((
                    500 * clear_span - wall_thickness + nominal_cover + top_bar / 200 + 500 * clear_span - nominal_cover - top_bar / 200)) / 2
            cx3 = (500 * clear_span - nominal_cover - top_bar / 200)
            cy1 = -4 * overall_depth - nominal_cover - top_bar / 200
            dot_centers = [(cx1, cy1), (cx2, cy1), (cx3, cy1)]  # Replace with the actual centers of the dots
            dot_radius = top_bar / 200
            top = 1
            create_dots_bb(dot_centers, dot_radius, top)

        elif (no_bars_top == 2):
            cx1 = (500 * clear_span - wall_thickness + nominal_cover + top_bar / 200)
            cx3 = (500 * clear_span - nominal_cover - top_bar / 200)
            cy1 = -4 * overall_depth - nominal_cover - top_bar / 200
            dot_centers = [(cx1, cy1), (cx3, cy1)]  # Replace with the actual centers of the dots
            dot_radius = top_bar / 200
            top = 1
            create_dots_bb(dot_centers, dot_radius, top)

        elif (no_bars_top == 4):
            cx1 = (500 * clear_span - wall_thickness + nominal_cover + top_bar / 200)
            cx2 = (500 * clear_span - wall_thickness + wall_thickness / 3 + top_bar / 100)
            cx3 = (500 * clear_span - wall_thickness + 2 * wall_thickness / 3 - top_bar / 100)
            cx4 = (500 * clear_span - nominal_cover - top_bar / 200)
            cy1 = -4 * overall_depth - nominal_cover - top_bar / 200
            dot_centers = [(cx1, cy1), (cx2, cy1), (cx3, cy1),
                           (cx4, cy1)]  # Replace with the actual centers of the dots
            dot_radius = top_bar / 200
            top = 1
            create_dots_bb(dot_centers, dot_radius, top)

        else:
            print("bars cannot be arranged")

        if (no_of_bars_bottom == 3):  # --------------------------------------------bottom
            x1 = (500 * clear_span - wall_thickness + nominal_cover + main_bar / 200)
            x2 = ((
                    500 * clear_span - wall_thickness + nominal_cover + main_bar / 200 + 500 * clear_span - nominal_cover - main_bar / 200)) / 2
            x3 = (500 * clear_span - nominal_cover - main_bar / 200)
            y2 = -5 * overall_depth + nominal_cover + main_bar / 200
            dot_centers1 = [(x1, y2), (x2, y2), (x3, y2)]  # Replace with the actual centers of the dots
            dot_radius1 = main_bar / 200
            bottom = 10
            create_dots_bb(dot_centers1, dot_radius1, bottom)
        elif (no_of_bars_bottom == 2):
            x1 = (500 * clear_span - wall_thickness + nominal_cover + main_bar / 200)
            x3 = (500 * clear_span - nominal_cover - main_bar / 200)
            y2 = -5 * overall_depth + nominal_cover + main_bar / 200
            dot_centers1 = [(x1, y2), (x3, y2)]  # Replace with the actual centers of the dots
            dot_radius1 = main_bar / 200
            bottom = 10
            create_dots_bb(dot_centers1, dot_radius1, bottom)
        elif (no_of_bars_bottom == 4):
            x1 = (500 * clear_span - wall_thickness + nominal_cover + main_bar / 200)
            x2 = (500 * clear_span - wall_thickness + wall_thickness / 3) + main_bar / 200
            x3 = (500 * clear_span - wall_thickness + 2 * wall_thickness / 3) - main_bar / 200
            x4 = (500 * clear_span - nominal_cover - main_bar / 200)
            y2 = -5 * overall_depth + nominal_cover + main_bar / 200
            dot_centers1 = [(x1, y2), (x2, y2), (x3, y2), (x4, y2)]  # Replace with the actual centers of the dots
            dot_radius1 = main_bar / 200
            bottom = 10
            create_dots_bb(dot_centers1, dot_radius1, bottom)
        else:
            print("bars cannot be arranged")
        text_string = "SECTION C-C"
        insert_point = (1000 * clear_span, -7 * overall_depth)  # X, Y coordinates where the text will be inserted.
        text_height = 1
        # Add text to the modelspace.
        msp.add_text(
            text_string,
            dxfattribs={
                'insert': insert_point,
                'height': text_height,
                # Additional attributes such as font, rotation, and color can be specified here.
                'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                'rotation': 0,
                'color': 7
            }
        )
        # section b-b
        msp.add_line((1000 * clear_span, -5 * overall_depth),
                     (1000 * clear_span - wall_thickness, -5 * overall_depth))  # bottom line
        msp.add_line((1000 * clear_span - wall_thickness, -5 * overall_depth),
                     (1000 * clear_span - wall_thickness, -4 * overall_depth))  # left line
        msp.add_line((1000 * clear_span - wall_thickness, -4 * overall_depth), (1000 * clear_span, -4 * overall_depth))
        msp.add_line((1000 * clear_span, -4 * overall_depth), (1000 * clear_span, -5 * overall_depth))
        # --stirrup cross
        nominal_cover = nominal_cover
        msp.add_line((1000 * clear_span - nominal_cover, -5 * overall_depth + nominal_cover),
                     (1000 * clear_span - wall_thickness + nominal_cover,
                      -5 * overall_depth + nominal_cover))  # bottom line
        msp.add_line((1000 * clear_span - wall_thickness + nominal_cover, -5 * overall_depth + nominal_cover),
                     (1000 * clear_span - wall_thickness + nominal_cover,
                      -4 * overall_depth - nominal_cover))  # left line
        msp.add_line((1000 * clear_span - wall_thickness + nominal_cover, -4 * overall_depth - nominal_cover),
                     (1000 * clear_span - nominal_cover, -4 * overall_depth - nominal_cover))
        msp.add_line((1000 * clear_span - nominal_cover, -4 * overall_depth - nominal_cover),
                     (1000 * clear_span - nominal_cover, -5 * overall_depth + nominal_cover))

        # cross section dimension
        dim3 = msp.add_linear_dim(
            base=(900 * clear_span, -5.5 * overall_depth),  # location of the dimension line
            p1=(1000 * clear_span, -5 * overall_depth),  # 1st measurement point
            p2=(1000 * clear_span - wall_thickness, -5 * overall_depth),  # 2nd measurement point
            dimstyle="EZDXF",  # default dimension style
        )
        msp.add_linear_dim(base=(900* clear_span, -3.5 * overall_depth),
                           p1=(1000 * clear_span - wall_thickness, -5 * overall_depth),
                           p2=(1000 * clear_span - wall_thickness, -4 * overall_depth),
                           angle=90).render()  # cross section

        def create_dots_cc(dot_centers, dot_radius, top):
            # Create solid dots at specified centers with given radius
            for center in dot_centers:
                # Create a HATCH entity with a solid fill
                hatch = msp.add_hatch()
                # Add a circular path to the hatch as its boundary
                edge_path = hatch.paths.add_edge_path()
                edge_path.add_arc(center=center, radius=dot_radius, start_angle=0, end_angle=360)
                # Set the hatch pattern to solid
                hatch.set_solid_fill()
                if (top == 1):
                    msp.add_diameter_dim(
                        center=center,
                        radius=dot_radius,
                        # text=None,
                        dimstyle="EZ_RADIUS",
                        angle=135,  # Adjust the angle as needed
                        override={'dimtad': 0, 'dimasz': .2, 'dimexo': 5000, "dimtoh": 1, "dimlfac": 100},
                        # 16MM # Moves dimension line outside if it overlaps with the circle
                        dxfattribs={'layer': 'dimensions'}
                    ).render()
                else:
                    msp.add_diameter_dim(
                        center=center,
                        radius=dot_radius,
                        dimstyle="EZ_RADIUS",
                        angle=135,  # Adjust the angle as needed
                        override={'dimtad': 0, 'dimasz': .2, 'dimexo': 5000, "dimtoh": 1, "dimlfac": 100},
                        # 12MM  # Moves dimension line outside if it overlaps with the circle
                        dxfattribs={'layer': 'dimensions'}
                    ).render()

            # Create a rectangle from the provided corners
            # Assuming rectangle_corners is a list of tuples [(x1, y1), (x2, y2), (x3, y3), (x4, y4)] in consecutive order
            # Save the document

        # Exam

        if (no_bars_top == 3):
            cx1 = (1000 * clear_span - wall_thickness + nominal_cover + top_bar / 200)
            cx2 = ((
                    1000 * clear_span - wall_thickness + nominal_cover + top_bar / 200 + 1000 * clear_span - nominal_cover - top_bar / 200)) / 2
            cx3 = (1000 * clear_span - nominal_cover - top_bar / 200)
            cy1 = -4 * overall_depth - nominal_cover - top_bar / 200
            dot_centers = [(cx1, cy1), (cx2, cy1), (cx3, cy1)]  # Replace with the actual centers of the dots
            dot_radius = top_bar / 200
            top = 1
            create_dots_bb(dot_centers, dot_radius, top)

        elif (no_bars_top == 2):
            cx1 = (1000 * clear_span - wall_thickness + nominal_cover + top_bar / 200)
            cx3 = (1000 * clear_span - nominal_cover - top_bar / 200)
            cy1 = -4 * overall_depth - nominal_cover - top_bar / 200
            dot_centers = [(cx1, cy1), (cx3, cy1)]  # Replace with the actual centers of the dots
            dot_radius = top_bar / 200
            top = 1
            create_dots_bb(dot_centers, dot_radius, top)

        elif (no_bars_top == 4):
            cx1 = (1000 * clear_span - wall_thickness + nominal_cover + top_bar / 200)
            cx2 = (1000 * clear_span - wall_thickness + wall_thickness / 3 + top_bar / 200)
            cx3 = (1000 * clear_span - wall_thickness + 2 * wall_thickness / 3 - top_bar / 200)
            cx4 = (1000 * clear_span - nominal_cover - top_bar / 200)
            cy1 = -4 * overall_depth - nominal_cover - top_bar / 200
            dot_centers = [(cx1, cy1), (cx2, cy1), (cx3, cy1),
                           (cx4, cy1)]  # Replace with the actual centers of the dots
            dot_radius = top_bar / 200
            top = 1
            create_dots_bb(dot_centers, dot_radius, top)

        else:
            print("bars cannot be arranged")

        if (no_of_bars_bottom == 3):  # --------------------------------------------bottom
            x1 = (1000 * clear_span - wall_thickness + nominal_cover + main_bar / 200)
            x2 = ((
                    1000 * clear_span - wall_thickness + nominal_cover + main_bar / 200 + 1000 * clear_span - nominal_cover - main_bar / 200)) / 2
            x3 = (1000 * clear_span - nominal_cover - main_bar / 200)
            y2 = -5 * overall_depth + nominal_cover + main_bar / 200
            dot_centers1 = [(x1, y2), (x2, y2), (x3, y2)]  # Replace with the actual centers of the dots
            dot_radius1 = main_bar / 200
            bottom = 10
            create_dots_bb(dot_centers1, dot_radius1, bottom)
        elif (no_of_bars_bottom == 2):
            x1 = (1000 * clear_span - wall_thickness + nominal_cover + main_bar / 200)
            x3 = (1000 * clear_span - nominal_cover - main_bar / 200)
            y2 = -5 * overall_depth + nominal_cover + main_bar / 200
            dot_centers1 = [(x1, y2), (x3, y2)]  # Replace with the actual centers of the dots
            dot_radius1 = main_bar / 200
            bottom = 10
            create_dots_cc(dot_centers1, dot_radius1, bottom)
        elif (no_of_bars_bottom == 4):
            x1 = (1000 * clear_span - wall_thickness + nominal_cover + main_bar / 200)
            x2 = (1000 * clear_span - wall_thickness + wall_thickness / 3) + main_bar / 200
            x3 = (1000 * clear_span - wall_thickness + 2 * wall_thickness / 3) - main_bar / 200
            x4 = (1000 * clear_span - nominal_cover - main_bar / 200)
            y2 = -5 * overall_depth + nominal_cover + main_bar / 200
            dot_centers1 = [(x1, y2), (x2, y2), (x3, y2), (x4, y2)]  # Replace with the actual centers of the dots
            dot_radius1 = main_bar / 200
            bottom = 10
            create_dots_cc(dot_centers1, dot_radius1, bottom)
        else:
            print("bars cannot be arranged")
        temp1 = overall_depth / 3
        if (overall_depth >= 7.5):
            if (temp1 > no_of_bars_side):
                if (no_of_bars_side == 2):
                    sx = -wall_thickness + nominal_cover
                    sy = (overall_depth * 2 / 3 - nominal_cover)
                    sx1 = clear_span * 1000 + wall_thickness - nominal_cover
                    sx3 = -wall_thickness + nominal_cover
                    sy3 = nominal_cover + overall_depth / 3
                    sx4 = clear_span * 1000 + wall_thickness - nominal_cover
                    msp.add_line((sx, sy), (sx1, sy))  # top side bar
                    msp.add_line((sx3, sy3), (sx4, sy3))  # bottom side bar

                elif (no_of_bars_side == 3):
                    print(no_of_bars_side)
                    sx = -wall_thickness + nominal_cover
                    sy = (overall_depth * .5 + nominal_cover)
                    sx1 = clear_span * 1000 + wall_thickness - nominal_cover
                    sx3 = -wall_thickness + nominal_cover
                    sy3 = nominal_cover + overall_depth * .25
                    sx4 = clear_span * 1000 + wall_thickness - nominal_cover
                    sy5 = nominal_cover + overall_depth * .75
                    sx5 = clear_span * 1000 + wall_thickness - nominal_cover
                    msp.add_line((sx, sy), (sx1, sy))  # top side bar
                    msp.add_line((sx3, sy3), (sx4, sy3))
                    msp.add_line((sx3, sy5), (sx5, sy5))  # bottom side bar

                def create_dots_bb(dot_centers, dot_radius, top):
                    # Create solid dots at specified centers with given radius
                    for center in dot_centers:
                        # Create a HATCH entity with a solid fill
                        hatch = msp.add_hatch()
                        # Add a circular path to the hatch as its boundary
                        edge_path = hatch.paths.add_edge_path()
                        edge_path.add_arc(center=center, radius=dot_radius, start_angle=0, end_angle=360)
                        # Set the hatch pattern to solid
                        hatch.set_solid_fill()
                        if (top == 1):
                            msp.add_diameter_dim(
                                center=center,
                                radius=dot_radius,
                                # text=None,
                                dimstyle="EZ_RADIUS",
                                angle=135,  # Adjust the angle as needed
                                override={'dimtad': 0, 'dimasz': .2, 'dimexo': 5000, "dimtoh": 1, "dimlfac": 100},
                                # 16MM # Moves dimension line outside if it overlaps with the circle
                                dxfattribs={'layer': 'dimensions'}
                            ).render()
                        else:
                            msp.add_diameter_dim(
                                center=center,
                                radius=dot_radius,
                                dimstyle="EZ_RADIUS",
                                angle=135,  # Adjust the angle as needed
                                override={'dimtad': 0, 'dimasz': .2, 'dimexo': 5000, "dimtoh": 1, "dimlfac": 100},
                                # 12MM  # Moves dimension line outside if it overlaps with the circle
                                dxfattribs={'layer': 'dimensions'}
                            ).render()

                if (no_of_bars_side == 3):  # --------------------------------------------left
                    x1 = (0 + nominal_cover + side_bar / 200)
                    y1 = -4.75 * overall_depth - nominal_cover + side_bar / 200
                    y2 = -4.5 * overall_depth - nominal_cover + side_bar / 200
                    y3 = -4.25 * overall_depth - nominal_cover + side_bar / 200
                    dot_centers1 = [(x1, y1), (x1, y2), (x1, y3)]  # Replace with the actual centers of the dots
                    dot_radius1 = side_bar / 200
                    bottom = 10
                    create_dots(dot_centers1, dot_radius1, bottom)
                elif (no_of_bars_side == 2):
                    x1 = (0 + nominal_cover + side_bar / 200)
                    y1 = -4.66 * overall_depth - nominal_cover + side_bar / 200
                    y2 = -4.33 * overall_depth - nominal_cover + side_bar / 200
                    dot_centers1 = [(x1, y2), (x1, y1)]  # Replace with the actual centers of the dots
                    dot_radius1 = side_bar / 200
                    bottom = 10
                    create_dots(dot_centers1, dot_radius1, bottom)
                elif (no_of_bars_side == 4):
                    x1 = (0 + nominal_cover + side_bar / 200)
                    y1 = -4.8 * overall_depth - nominal_cover + side_bar / 200
                    y2 = -4.6 * overall_depth - nominal_cover + side_bar / 200
                    y3 = -4.4 * overall_depth - nominal_cover + side_bar / 200
                    y3 = -4.2 * overall_depth - nominal_cover + side_bar / 200
                    dot_centers1 = [(x1, y1), (x2, y2), (x3, y3),
                                    (x4, y4)]  # Replace with the actual centers of the dots
                    dot_radius1 = side_bar / 200
                    bottom = 10
                    create_dots(dot_centers1, dot_radius1, bottom)
                else:
                    print("bars cannot be arranged")
                if (no_of_bars_side == 3):  # --------------------------------------------right
                    x1 = (wall_thickness - nominal_cover - side_bar / 200)
                    y1 = -4.75 * overall_depth - nominal_cover + side_bar / 200
                    y2 = -4.5 * overall_depth - nominal_cover + side_bar / 200
                    y3 = -4.25 * overall_depth - nominal_cover + side_bar / 200
                    dot_centers1 = [(x1, y1), (x1, y2), (x1, y3)]  # Replace with the actual centers of the dots
                    dot_radius1 = side_bar / 200
                    bottom = 10
                    create_dots(dot_centers1, dot_radius1, bottom)
                elif (no_of_bars_side == 2):
                    x1 = (wall_thickness - nominal_cover - side_bar / 200)
                    y1 = -4.66 * overall_depth - nominal_cover + side_bar / 200
                    y2 = -4.33 * overall_depth - nominal_cover + side_bar / 200
                    dot_centers1 = [(x1, y2), (x1, y1)]  # Replace with the actual centers of the dots
                    dot_radius1 = side_bar / 200
                    bottom = 10
                    create_dots(dot_centers1, dot_radius1, bottom)
                elif (no_of_bars_side == 4):
                    x1 = (wall_thickness - nominal_cover - side_bar / 200)
                    y1 = -4.8 * overall_depth - nominal_cover + side_bar / 200
                    y2 = -4.6 * overall_depth - nominal_cover + side_bar / 200
                    y3 = -4.4 * overall_depth - nominal_cover + side_bar / 200
                    y3 = -4.2 * overall_depth - nominal_cover + side_bar / 200
                    dot_centers1 = [(x1, y1), (x1, y2), (x1, y3),
                                    (x1, y4)]  # Replace with the actual centers of the dots
                    dot_radius1 = side_bar / 200
                    bottom = 10
                    create_dots(dot_centers1, dot_radius1, bottom)
                else:
                    print("bars cannot be arranged")
                    # ---------------for section bb
                if (no_of_bars_side == 3):  # --------------------------------------------left-bb
                    x1 = (500 * clear_span - wall_thickness + nominal_cover + top_bar / 200)
                    y1 = -4.75 * overall_depth - nominal_cover + side_bar / 200
                    y2 = -4.5 * overall_depth - nominal_cover + side_bar / 200
                    y3 = -4.25 * overall_depth - nominal_cover + side_bar / 200
                    dot_centers1 = [(x1, y1), (x1, y2), (x1, y3)]  # Replace with the actual centers of the dots
                    dot_radius1 = side_bar / 200
                    bottom = 10
                    create_dots(dot_centers1, dot_radius1, bottom)
                elif (no_of_bars_side == 2):
                    x1 = (500 * clear_span - wall_thickness + nominal_cover + top_bar / 200)
                    y1 = -4.66 * overall_depth - nominal_cover + side_bar / 200
                    y2 = -4.33 * overall_depth - nominal_cover + side_bar / 200
                    dot_centers1 = [(x1, y2), (x1, y1)]  # Replace with the actual centers of the dots
                    dot_radius1 = side_bar / 200
                    bottom = 10
                    create_dots(dot_centers1, dot_radius1, bottom)
                elif (no_of_bars_side == 4):
                    x1 = (500 * clear_span - wall_thickness + nominal_cover + top_bar / 200)
                    y1 = -4.8 * overall_depth - nominal_cover + side_bar / 200
                    y2 = -4.6 * overall_depth - nominal_cover + side_bar / 200
                    y3 = -4.4 * overall_depth - nominal_cover + side_bar / 200
                    y3 = -4.2 * overall_depth - nominal_cover + side_bar / 200
                    dot_centers1 = [(x1, y1), (x2, y2), (x3, y3),
                                    (x4, y4)]  # Replace with the actual centers of the dots
                    dot_radius1 = side_bar / 200
                    bottom = 10
                    create_dots(dot_centers1, dot_radius1, bottom)
                else:
                    print("bars cannot be arranged")
                if (no_of_bars_side == 3):  # --------------------------------------------right -bb
                    x1 = (500 * clear_span - nominal_cover - side_bar / 200)
                    y1 = -4.75 * overall_depth - nominal_cover + side_bar / 200
                    y2 = -4.5 * overall_depth - nominal_cover + side_bar / 200
                    y3 = -4.25 * overall_depth - nominal_cover + side_bar / 200
                    dot_centers1 = [(x1, y1), (x1, y2), (x1, y3)]  # Replace with the actual centers of the dots
                    dot_radius1 = side_bar / 200
                    bottom = 10
                    create_dots(dot_centers1, dot_radius1, bottom)
                elif (no_of_bars_side == 2):
                    x1 = (500 * clear_span - nominal_cover - side_bar / 200)
                    y1 = -4.66 * overall_depth - nominal_cover + side_bar / 200
                    y2 = -4.33 * overall_depth - nominal_cover + side_bar / 200
                    dot_centers1 = [(x1, y2), (x1, y1)]  # Replace with the actual centers of the dots
                    dot_radius1 = side_bar / 200
                    bottom = 10
                    create_dots(dot_centers1, dot_radius1, bottom)
                elif (no_of_bars_side == 4):
                    x1 = (500 * clear_span - nominal_cover - side_bar / 200)
                    y1 = -4.8 * overall_depth - nominal_cover + side_bar / 200
                    y2 = -4.6 * overall_depth - nominal_cover + side_bar / 200
                    y3 = -4.4 * overall_depth - nominal_cover + side_bar / 200
                    y3 = -4.2 * overall_depth - nominal_cover + side_bar / 200
                    dot_centers1 = [(x1, y1), (x1, y2), (x1, y3),
                                    (x1, y4)]  # Replace with the actual centers of the dots
                    dot_radius1 = side_bar / 200
                    bottom = 10
                    create_dots(dot_centers1, dot_radius1, bottom)
                else:
                    print("bars cannot be arranged")
                if (no_of_bars_side == 3):  # --------------------------------------------left-bb
                    x1 = (1000 * clear_span - wall_thickness + nominal_cover + top_bar / 200)
                    y1 = -4.75 * overall_depth - nominal_cover + side_bar / 200
                    y2 = -4.5 * overall_depth - nominal_cover + side_bar / 200
                    y3 = -4.25 * overall_depth - nominal_cover + side_bar / 200
                    dot_centers1 = [(x1, y1), (x1, y2), (x1, y3)]  # Replace with the actual centers of the dots
                    dot_radius1 = side_bar / 200
                    bottom = 10
                    create_dots(dot_centers1, dot_radius1, bottom)
                elif (no_of_bars_side == 2):
                    x1 = (1000 * clear_span - wall_thickness + nominal_cover + top_bar / 200)
                    y1 = -4.66 * overall_depth - nominal_cover + side_bar / 200
                    y2 = -4.33 * overall_depth - nominal_cover + side_bar / 200
                    dot_centers1 = [(x1, y2), (x1, y1)]  # Replace with the actual centers of the dots
                    dot_radius1 = side_bar / 200
                    bottom = 10
                    create_dots(dot_centers1, dot_radius1, bottom)
                elif (no_of_bars_side == 4):
                    x1 = (1000 * clear_span - wall_thickness + nominal_cover + top_bar / 200)
                    y1 = -4.8 * overall_depth - nominal_cover + side_bar / 200
                    y2 = -4.6 * overall_depth - nominal_cover + side_bar / 200
                    y3 = -4.4 * overall_depth - nominal_cover + side_bar / 200
                    y3 = -4.2 * overall_depth - nominal_cover + side_bar / 200
                    dot_centers1 = [(x1, y1), (x2, y2), (x3, y3),
                                    (x4, y4)]  # Replace with the actual centers of the dots
                    dot_radius1 = side_bar / 200
                    bottom = 10
                    create_dots(dot_centers1, dot_radius1, bottom)
                else:
                    print("bars cannot be arranged")
                if (no_of_bars_side == 3):  # --------------------------------------------right -cc
                    x1 = (1000 * clear_span - nominal_cover - main_bar / 200)
                    y1 = -4.75 * overall_depth - nominal_cover + side_bar / 200
                    y2 = -4.5 * overall_depth - nominal_cover + side_bar / 200
                    y3 = -4.25 * overall_depth - nominal_cover + side_bar / 200
                    dot_centers1 = [(x1, y1), (x1, y2), (x1, y3)]  # Replace with the actual centers of the dots
                    dot_radius1 = side_bar / 200
                    bottom = 10
                    create_dots(dot_centers1, dot_radius1, bottom)
                elif (no_of_bars_side == 2):
                    x1 = (1000 * clear_span - nominal_cover - main_bar / 200)
                    y1 = -4.66 * overall_depth - nominal_cover + side_bar / 200
                    y2 = -4.33 * overall_depth - nominal_cover + side_bar / 200
                    dot_centers1 = [(x1, y2), (x1, y1)]  # Replace with the actual centers of the dots
                    dot_radius1 = side_bar / 200
                    bottom = 10
                    create_dots(dot_centers1, dot_radius1, bottom)
                elif (no_of_bars_side == 4):
                    x1 = (1000 * clear_span - nominal_cover - main_bar / 200)
                    y1 = -4.8 * overall_depth - nominal_cover + side_bar / 200
                    y2 = -4.6 * overall_depth - nominal_cover + side_bar / 200
                    y3 = -4.4 * overall_depth - nominal_cover + side_bar / 200
                    y3 = -4.2 * overall_depth - nominal_cover + side_bar / 200
                    dot_centers1 = [(x1, y1), (x1, y2), (x1, y3),
                                    (x1, y4)]  # Replace with the actual centers of the dots
                    dot_radius1 = side_bar / 200
                    bottom = 10
                    create_dots(dot_centers1, dot_radius1, bottom)
                else:
                    print("bars cannot be arranged")
        dim.render()
        file = "SimplySupported.dxf"
        doc.saveas(file)
        print("Drwaing is created for Simply supported beam as:", file)
        # Save the document as a DXF file
        filename = f'SimplySupported_{o_d}x{round(wall_thickness * 100, 1)}.dxf'
        filepath = os.path.join('generated_files', filename)
        os.makedirs('generated_files', exist_ok=True)
        doc.saveas(filepath)
        return send_file(filepath, as_attachment=True, download_name=filename)
    # Create a new DXF document

    # Save the DXF file
    if (beam_type == "Cantilever"):
        filename = f'Cantilever_{provided_depth}x{round(wall_thickness * 100, 1)}.dxf'
        filepath = os.path.join('generated_files', filename)
        os.makedirs('generated_files', exist_ok=True)
        doc.saveas(filepath)
        return send_file(filepath, as_attachment=True, download_name=filename)


if __name__ == '__main__':
    app.run(debug=True)
