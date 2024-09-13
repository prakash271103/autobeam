import os
import sys
from datetime import datetime
import matplotlib.pyplot as plt
import numpy as np
from ezdxf.math import ConstructionArc
from flask import Flask, render_template, send_file, request

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
    from ezdxf.render import ARROWS


    beam_type = request.form['type']
    print(beam_type)
    if beam_type == "Cantilever":
        beam_length = float(request.form['beam_length'])
        clear_span = beam_length
        exposure = request.form['exposure']
        cd = 750
        wall_thickness = float(request.form['wall_thickness'])
        span_d = 5
        fck = int(request.form['fck'])
        fy = int(request.form['fy'])
        udl = float(request.form['udl'])
        print("inputs")
        print(beam_length)
        print(exposure)
        print(wall_thickness)
        print(fck)
        print(fy)
        print(udl)
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
        udl=udl+self_weight

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
                main_bar = [12, 16, 20, 25, 32, 40,50]
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
                    return("The Required Diameter of the bar exceeds 40mm")

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
            if provided_depth >= 750:
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
                return(" revise section Section Fails under deflection")
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
            x3 = -cd + nominal_cover / 100+ld/300
            x31 = clear_span * 800
            y3 = nominal_cover / 100
            x4 = clear_span * 1000 + - nominal_cover / 100
            y4 = nominal_cover / 100
            x5 = -wall_thickness / 2
            y5 = overall_depth / 1.2
            x6 = clear_span * 1000 + 2 * wall_thickness / 4
            y6 = overall_depth / 1.2

            # Create a Line
            msp.add_line((x+2*top_bar/100, y), (x1, y1))  # top bar
            msp.add_line((x, y-2*top_bar/100), (x, -ld / 100))
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

            # hook---------------------------------------
            msp.add_line((nominal_cover + top_bar / 100, -4 * overall_depth - nominal_cover), (
            nominal_cover + top_bar / 100 + 2 * top_bar / 100, -4 * overall_depth - nominal_cover - 2 * top_bar / 100))
            msp.add_line((nominal_cover, -4 * overall_depth - nominal_cover - top_bar / 100), (
            nominal_cover + 2 * top_bar / 100, -4 * overall_depth - nominal_cover - top_bar / 100 - 2 * top_bar / 100))
            attribs = {'layer': '0', 'color': 7}
            # top -left-----------------
            startleft_pointtl = (x + 2*top_bar / 100, y)
            endleft_pointtl = (x, y -2*top_bar / 100)
            arctl = ConstructionArc.from_2p_radius(
                start_point=startleft_pointtl,
                end_point=endleft_pointtl,
                radius=main_bar / 50  # left fillet
            )
            arctl.add_to_layout(msp, dxfattribs=attribs)

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
            )
            # hatch
            hatch = msp.add_hatch()
            hatch.set_pattern_fill("ANSI32", scale=.1)
            hatch.paths.add_polyline_path(
                [(0, 0), (-cd, 0), (-cd, -overall_depth), (0, -overall_depth)], is_closed=True
            )
            '''
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
            #hook -b-b
            msp.add_line(
                (500 * clear_span - wall_thickness + nominal_cover + top_bar / 100, -4 * overall_depth - nominal_cover),
                (
                    500 * clear_span - wall_thickness + nominal_cover + top_bar / 100 + 2 * top_bar / 100,
                    -4 * overall_depth - nominal_cover - 2 * top_bar / 100))
            msp.add_line(
                (500 * clear_span - wall_thickness + nominal_cover, -4 * overall_depth - nominal_cover - top_bar / 100),
                (
                    500 * clear_span - wall_thickness + nominal_cover + 2 * top_bar / 100,
                    -4 * overall_depth - nominal_cover - top_bar / 100 - 2 * top_bar / 100))


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
            insert_point = (1000 * clear_span-wall_thickness, -7 * overall_depth)  # X, Y coordinates where the text will be inserted.
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
            # hook---------------------------------------
            msp.add_line((1000 * clear_span - wall_thickness + nominal_cover + top_bar / 100,
                          -4 * overall_depth - nominal_cover), (
                         1000 * clear_span - wall_thickness + nominal_cover + top_bar / 100 + 2 * top_bar / 100,
                         -4 * overall_depth - nominal_cover - 2 * top_bar / 100))
            msp.add_line((1000 * clear_span - wall_thickness + nominal_cover,
                          -4 * overall_depth - nominal_cover - top_bar / 100), (
                         1000 * clear_span - wall_thickness + nominal_cover + 2 * top_bar / 100,
                         -4 * overall_depth - nominal_cover - top_bar / 100 - 2 * top_bar / 100))

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
            if provided_depth >= 750:
                sideast = 0.0005 * wall_thickness *  provided_depth
                side_bar = [12, 16, 20, 25, 32, 40]
                results1 = []

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
                        msp.add_line((sx+ld/300+top_bar/50, sy), (sx1, sy))  # top side bar
                        msp.add_line((sx3+ld*2/300+top_bar*2/100, sy3), (sx4, sy3))  # bottom side bar
                        #ld for side face
                        msp.add_line((sx3 + ld * 2 / 300, sy3-top_bar/50), (sx3+ld*2/300, sy3-ld/100-overall_depth/3))
                        attribs = {'layer': '0', 'color': 7}
                        # top -left-----------------
                        startleft_pointtls =  (sx3+ld*2/300+top_bar*2/100, sy3)
                        endleft_pointtls = (sx3 + ld/150, sy3-top_bar/50)
                        arctls = ConstructionArc.from_2p_radius(
                            start_point=startleft_pointtls,
                            end_point=endleft_pointtls,
                            radius=main_bar / 50  # left fillet
                        )
                        arctls.add_to_layout(msp, dxfattribs=attribs)
                        #1st side face
                        msp.add_line((sx + ld * 1 / 300, sy - top_bar / 50),
                                     (sx + ld * 1 / 300, sy -ld *1/ 100 - overall_depth *2/ 3))
                        startleft_pointtlss = (sx + ld * 1 / 300 + top_bar * 2 / 100, sy)
                        endleft_pointtlss = (sx + ld / 300, sy - top_bar / 50)
                        arctlss = ConstructionArc.from_2p_radius(
                            start_point=startleft_pointtlss,
                            end_point=endleft_pointtlss,
                            radius=main_bar / 50  # left fillet
                        )
                        arctlss.add_to_layout(msp, dxfattribs=attribs)


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
                        msp.add_line((sx+ld/200+top_bar/50, sy), (sx1, sy))  # mid side bar
                        msp.add_line((sx3+ld*3/400+top_bar/50, sy3), (sx4, sy3))#bottom
                        msp.add_line((sx3+ld*1/400+top_bar/50, sy5), (sx5, sy5))  # top side bar
                        # ld for side face
                        msp.add_line((sx3 + ld * 1 / 400, sy5 - top_bar / 50),
                                     (sx3 + ld * 1 / 400, sy5 - ld / 100 - overall_depth / 3))
                        attribs = {'layer': '0', 'color': 7}
                        # top -left-----------------
                        startleft_pointtls = (sx3 + ld *1  / 400 + top_bar * 2 / 100, sy5)
                        endleft_pointtls = (sx3 + ld*1 / 400, sy5 - top_bar / 50)
                        arctls = ConstructionArc.from_2p_radius(
                            start_point=startleft_pointtls,
                            end_point=endleft_pointtls,
                            radius=main_bar / 50  # left fillet
                        )
                        arctls.add_to_layout(msp, dxfattribs=attribs)
                        # 1st side face
                        msp.add_line((sx + ld * 2/ 400, sy - top_bar / 50),
                                     (sx + ld * 2/ 400, sy - ld * 1 / 100 - overall_depth * 1/ 3))
                        startleft_pointtlss = (sx + ld * 2 / 400 + top_bar * 2 / 100, sy)
                        endleft_pointtlss = (sx + ld *2/ 400, sy - top_bar / 50)
                        arctlss = ConstructionArc.from_2p_radius(
                            start_point=startleft_pointtlss,
                            end_point=endleft_pointtlss,
                            radius=main_bar / 50  # left fillet
                        )
                        arctlss.add_to_layout(msp, dxfattribs=attribs)
                        # 1st side face
                        msp.add_line((sx + ld * 3 / 400, sy3 - top_bar / 50),
                                     (sx + ld * 3 / 400, sy3 - ld * 1 / 100 - overall_depth * 1 / 3))
                        startleft_pointtlsss = (sx + ld * 3 / 400 + top_bar * 2 / 100, sy3)
                        endleft_pointtlsss = (sx + ld * 3 / 400, sy3 - top_bar / 50)
                        arctlsss = ConstructionArc.from_2p_radius(
                            start_point=startleft_pointtlsss,
                            end_point=endleft_pointtlsss,
                            radius=main_bar / 50  # left fillet
                        )
                        arctlsss.add_to_layout(msp, dxfattribs=attribs)

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
            if (astmax < astmin or astmax < ast):
                return("Revise Section Tensile Reinforcement exceeds 4 %")
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
            if provided_depth >= 750:
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
                stdia =  8
                leg =2

                sv = 0.87 * fy * effective_depth * leg * 0.78539816339744830961566084581988 * stdia ** 2 / Vus
                print(sv)
                spacing = min(0.75 * effective_depth, 300)
                max_spacing = (spacing // 25) * 25
                # print(max_spacing)
                print("Provide Φ", stdia, "- mm ", leg, "vertical stirrups @", max_spacing, "c/c")
            elif (tv <= tc):
                stdia =  8
                leg =  2

                sv = 0.87 * fy * leg * 0.78539816339744830961566084581988 * stdia ** 2 / (0.4 * wall_thickness)
                spacing = min(0.75 * effective_depth, 300)
                max_spacing = (spacing // 25) * 25
                # print(max_spacing)
                print("Provide Φ", stdia, "- mm ", leg, "vertical stirrups @", max_spacing, "c/c")
            else:
                return("Revise section (per Cl. 40.2.3, IS 456: 2000, pp. 72")
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
            x = 10
            no_of_bars_shear_face = math.ceil((as1 / 2) / (0.785 * x))
            spacing_of_bars = provided_depth - nominal_cover * 2 - stdia * 2 - main_bar / 2 - bottom_bar_provided / 2
            no_of_bars_shear = math.ceil((spacing_of_bars / wall_thickness) - 1)
            print("shear r", no_of_bars_shear)
            if (allowablespan > Actualspan):
                print(" The section is safe under deflection")
            else:
                return(" revise section ,Section Fails under Deflection")
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
            # hook---------------------------------------
            msp.add_line((nominal_cover + top_bar / 100, -4 * overall_depth - nominal_cover), (
                nominal_cover + top_bar / 100 + 2 * top_bar / 100,
                -4 * overall_depth - nominal_cover - 2 * top_bar / 100))
            msp.add_line((nominal_cover, -4 * overall_depth - nominal_cover - top_bar / 100), (
                nominal_cover + 2 * top_bar / 100,
                -4 * overall_depth - nominal_cover - top_bar / 100 - 2 * top_bar / 100))

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

            # hook -b-b
            msp.add_line(
                (500 * clear_span - wall_thickness + nominal_cover + top_bar / 100, -4 * overall_depth - nominal_cover),
                (
                    500 * clear_span - wall_thickness + nominal_cover + top_bar / 100 + 2 * top_bar / 100,
                    -4 * overall_depth - nominal_cover - 2 * top_bar / 100))
            msp.add_line(
                (500 * clear_span - wall_thickness + nominal_cover, -4 * overall_depth - nominal_cover - top_bar / 100),
                (
                    500 * clear_span - wall_thickness + nominal_cover + 2 * top_bar / 100,
                    -4 * overall_depth - nominal_cover - top_bar / 100 - 2 * top_bar / 100))

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
            insert_point = (1000 * clear_span-wall_thickness, -7 * overall_depth)  # X, Y coordinates where the text will be inserted.
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

            # hook---------------------------------------
            msp.add_line((1000 * clear_span - wall_thickness + nominal_cover + top_bar / 100,
                          -4 * overall_depth - nominal_cover), (
                         1000 * clear_span - wall_thickness + nominal_cover + top_bar / 100 + 2 * top_bar / 100,
                         -4 * overall_depth - nominal_cover - 2 * top_bar / 100))
            msp.add_line((1000 * clear_span - wall_thickness + nominal_cover,
                          -4 * overall_depth - nominal_cover - top_bar / 100), (
                         1000 * clear_span - wall_thickness + nominal_cover + 2 * top_bar / 100,
                         -4 * overall_depth - nominal_cover - top_bar / 100 - 2 * top_bar / 100))

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
        ll=live_load
        num_point_loads = 0
        point_loads = []
        print(beam_length)
        print(exposure_condition)
        print(wall_thickness)
        print(fck)
        print(fy)
        print(live_load)

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

            d = l / spanratio
            # Assuming the span/depth ratio is 15
            spant=spanratio
            nominal_cover = get_nominal_cover(exposure_condition)
            print(d)
            effective_cover = nominal_cover + min_bar_dia + (max_bar_dia / 2)
            print("effective cover: ", effective_cover)
            overall_depth = round(d + effective_cover, -2)
            effective_depth = overall_depth - effective_cover
            return effective_depth, overall_depth, l, effective_cover, nominal_cover,spant

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
        effective_depth, overall_depth, l, effective_cover, nominal_cover ,spant= get_effective_depth(clear_span,
                                                                                                wall_thickness,
                                                                                                exposure_condition,
                                                                                                min_bar_dia,
                                                                                                max_bar_dia)
        b = wall_thickness
        o_d = round(overall_depth, -2)
        print("Overall depth:", o_d)
        print("effective_depth: ", effective_depth)
        print("Assumed width of beam:", b)
        wtt = wall_thickness
        odt = o_d
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


        max_bending_moment = max_bending_moment
        print("Maximum bending moment:", max_bending_moment, "kNm")
        ultimate_bending_moment = 1.5 * max_bending_moment
        print("Ultimate bending moment:", ultimate_bending_moment, "kNm")
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
            pc = 100 * ab / (b * effective_depth)
            # print(main_bar, no_of_bars, pt)
            top_bar_provided = top_bar
            # no_of_bars = round(ast / (0.78539816339744830961566084581988 * main_bar ** 2), 0)
            print("Provide", no_of_bars_top, "-Φ", top_bar, " mm as main bars at the top")

            print("Percentage of steel provided(Compression Reinforcement): ", pc)
            #Side-face Reinforcement
            if o_d >= 750:
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



            print("modification factor: ", mf)
            if (allowablespan > Actualspan):
                print(" The section is safe under deflection")
            else:
                return(" revise section ,Section Fails under Deflection")



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
                pc = 100 * ab / (b * effective_depth)
                # print(main_bar, no_of_bars, pt)
                top_bar_provided = top_bar
                print("provide", no_of_bars_top, "-Φ", top_bar, " mm as main bars at the top")

                print("percentage of steel provided(Compression Reinforcement): ", pc)
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
                pc = 100 * ab / (b * effective_depth)
                # print(main_bar, no_of_bars, pt)
                top_bar_provided = top_bar
                print("provide", no_of_bars_top, "-Φ", top_bar, " mm as main bars at the top")
                print("percentage of steel provided(Compression Reinforcement): ", pc)
            #side face
            if o_d >= 750:
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



            # print("modification factor: ", mf)
            if (allowablespan > Actualspan):
                print(" The section is safe under deflection")
            else:
                return(" revise section Section Fails under deflection")
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
        # column beam ld-----------------------------------------------------------------------------------------------------------
        msp.add_line((x, y-main_bar/100),
                     (x,.6*overall_depth))#top left
        msp.add_line((x3,y3+main_bar/100),(x3,y4+.4*overall_depth))#bottom left
        msp.add_line((x1,y1-main_bar/100),(x1,.6*overall_depth))#top left
        msp.add_line((x4,y4+main_bar/100),(x4,y4+.4*overall_depth))
        #------------------top left join fillet
        attribs = {'layer': '0', 'color': 7}
        # top -left-----------------
        startleft_pointtl =  (x+main_bar/100, y)
        endleft_pointtl = (x, y-main_bar/100)
        arctl = ConstructionArc.from_2p_radius(
            start_point=startleft_pointtl,
            end_point=endleft_pointtl,
            radius=main_bar / 100 + main_bar / 400  # left fillet
        )
        arctl.add_to_layout(msp, dxfattribs=attribs)
        # ------------------bot left join fillet
        attribs = {'layer': '0', 'color': 7}
        # bot -left-----------------
        startleft_pointbl = (x3, y3 + main_bar / 100)
        endleft_pointbl = (x3 + main_bar / 100, y3)
        arcbl = ConstructionArc.from_2p_radius(
            start_point=startleft_pointbl,
            end_point=endleft_pointbl,
            radius=main_bar / 100 + main_bar / 400  # left fillet
        )
        arcbl.add_to_layout(msp, dxfattribs=attribs)
        # top -right-----------------
        startleft_pointtl = (x1, y - main_bar / 100)
        endleft_pointtl = (x1 - main_bar / 100, y)
        arctl = ConstructionArc.from_2p_radius(
            start_point=startleft_pointtl,
            end_point=endleft_pointtl,
            radius=main_bar / 100 + main_bar / 400  # left fillet
        )
        arctl.add_to_layout(msp, dxfattribs=attribs)
        # ------------------bot left join fillet
        attribs = {'layer': '0', 'color': 7}
        # bot -right-----------------
        startleft_pointbl = (x4 - main_bar / 100, y3)
        endleft_pointbl = (x4, y3 + main_bar / 100)
        arcbl = ConstructionArc.from_2p_radius(
            start_point=startleft_pointbl,
            end_point=endleft_pointbl,
            radius=main_bar / 100 + main_bar / 400  # left fillet
        )
        arcbl.add_to_layout(msp, dxfattribs=attribs)
        # Create a Line
        msp.add_line((x+main_bar/100, y), (x1-main_bar/100, y1))  # top bar
        msp.add_line((x3+main_bar/100, y3), (x4-main_bar/100, y4))  # bottom bar
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
        msp.add_line((0 + nominal_cover+main_bar/100, -5 * overall_depth + nominal_cover),
                     (wall_thickness - nominal_cover-main_bar/100, -5 * overall_depth + nominal_cover))  # bottom line
        msp.add_line((0 + nominal_cover, -5 * overall_depth + nominal_cover+main_bar/100),
                     (0 + nominal_cover, -4 * overall_depth - nominal_cover-top_bar/100))  # left line
        msp.add_line((0 + nominal_cover+top_bar/100, -4 * overall_depth - nominal_cover),
                     (wall_thickness - nominal_cover-top_bar/100, -4 * overall_depth - nominal_cover))
        msp.add_line((wall_thickness - nominal_cover, -4 * overall_depth - nominal_cover-top_bar/100),
                     (wall_thickness - nominal_cover, -5 * overall_depth + nominal_cover+main_bar/100))
        #hook a-a----------------------------------
        text_content = f"Y-{stdia} Stirrup @ {max_spacing} mm c/c"
        text_location = (wall_thickness+ nominal_cover + top_bar / 100,
                         -4.45 * overall_depth - nominal_cover)  # Positioning the text outside the rectangle
        dimstyle = msp.doc.dimstyles.get('EZDXF')  # Get the 'Standard' DIMSTYLE or create a new one
        dimstyle.dxf.dimasz = nominal_cover * 3
        msp.add_text(
            text_content,
            dxfattribs={
                'height': .2,  # Text height
                'layer': 'TEXT',  # Optional: specify a layer for the text
                'color': 7,
                # Optional: specify text color
                'insert': text_location,  # Position of the text
            }
        )
        leader_points = [
            (+ nominal_cover, -4.5 * overall_depth - nominal_cover),
            # Start inside the rectangle
            (  wall_thickness / 2, -4.4 * overall_depth - nominal_cover),
            # First bend point
            (wall_thickness + top_bar / 100, -4.4 * overall_depth - nominal_cover)
            # End point at the text location
        ]

        msp.add_leader(leader_points, dxfattribs={
            'color': 7,
            'dimstyle': 'EZDXF'})
        attribs = {'layer': '0', 'color': 7}
#bottom -left-----------------
        startleft_point = (nominal_cover , -5 * overall_depth + nominal_cover+main_bar/100)
        endleft_point = (nominal_cover+main_bar/100, -5 * overall_depth + nominal_cover )
        arc2 = ConstructionArc.from_2p_radius(
            start_point=startleft_point,
            end_point=endleft_point,
            radius=main_bar / 100 + main_bar / 400  # left fillet
        )
        arc2.add_to_layout(msp, dxfattribs=attribs)
        startleft_point = (
            wall_thickness - nominal_cover-main_bar/100, -5 * overall_depth + nominal_cover )
        endleft_point = (
             wall_thickness - nominal_cover , -5 * overall_depth + nominal_cover+main_bar/100)
        # bottom right
        arc2 = ConstructionArc.from_2p_radius(
            start_point=startleft_point,
            end_point=endleft_point,
            radius=main_bar / 100 + main_bar / 400  # left fillet
        )
        arc2.add_to_layout(msp, dxfattribs=attribs)
        # top right-------------------------------------
        endleft_point1 =  (wall_thickness- nominal_cover - top_bar / 100, -4 * overall_depth - nominal_cover)
        startleft_point1 = (wall_thickness - nominal_cover, -4 * overall_depth - nominal_cover - top_bar / 100)
        arc3 = ConstructionArc.from_2p_radius(
            start_point=startleft_point1,
            end_point=endleft_point1,
            radius=top_bar/100  # left fillet
        )
        arc3.add_to_layout(msp, dxfattribs=attribs)
        # top-left-----------------------------------------------------
        endleft_point2 = (1000 * clear_span - nominal_cover - top_bar / 100, -4 * overall_depth - nominal_cover)
        startleft_point2 = (1000 * clear_span - nominal_cover, -4 * overall_depth - nominal_cover - top_bar / 100)
        arc4 = ConstructionArc.from_2p_radius(
            start_point=startleft_point2,
            end_point=endleft_point2,
            radius=top_bar / 100  # left fillet
        )
        arc4.add_to_layout(msp, dxfattribs=attribs)
        # hook---------------------------------------
        msp.add_line((  nominal_cover + top_bar / 100, -4 * overall_depth - nominal_cover), (nominal_cover + top_bar / 100 + 2 * top_bar / 100,-4 * overall_depth - nominal_cover - 2 * top_bar / 100))
        msp.add_line((  nominal_cover, -4 * overall_depth - nominal_cover - top_bar / 100), (nominal_cover + 2 * top_bar / 100,-4 * overall_depth - nominal_cover - top_bar / 100 - 2 * top_bar / 100))
        # hook-fillet
        startleft_point3 = (nominal_cover + top_bar / 100, -4 * overall_depth - nominal_cover)
        endleft_point3 = (nominal_cover, -4 * overall_depth - nominal_cover - top_bar / 100)
        arc5 = ConstructionArc.from_2p_radius(
            start_point=startleft_point3,
            end_point=endleft_point3,
            radius=top_bar / 100  # left fillet
        )
        arc5.add_to_layout(msp, dxfattribs=attribs)




        X22 = clear_span * 1000
        X11 = clear_span

        text_content = f"{no_of_bars_bottom}-Y{main_bar} "
        text_location = (
            X11 + wall_thickness * 2, y4 - .55 * overall_depth)  # Positioning the text outside the rectangle
        dimstyle = msp.doc.dimstyles.get('EZDXF')  # Get the 'Standard' DIMSTYLE or create a new one
        dimstyle.dxf.dimasz = nominal_cover * 3
        msp.add_text(
            text_content,
            dxfattribs={
                'height': wall_thickness / 4,  # Text height
                'layer': 'TEXT',  # Optional: specify a layer for the text
                'color': 7,
                # Optional: specify text color
                'insert': text_location,  # Position of the text
            }
        )
        leader_points = [
            (X11 + wall_thickness, y4),  # Start inside the rectangle
            (X11 + wall_thickness, y4 - .5 * overall_depth),  # First bend point
            (X11 + 2 * wall_thickness, -.5 * overall_depth + y4)  # End point at the text location
        ]

        msp.add_leader(leader_points, dxfattribs={
            'color': 7,
            'dimstyle': 'EZDXF'})
        # -----top bar

        text_content = f"{no_of_bars_top}-Y{top_bar} + 2-Y{main_bar} "
        text_location = (
        X11 + wall_thickness * 2, 2 * overall_depth - y3 * 3)  # Positioning the text outside the rectangle
        dimstyle = msp.doc.dimstyles.get('EZDXF')  # Get the 'Standard' DIMSTYLE or create a new one
        dimstyle.dxf.dimasz = nominal_cover * 3
        msp.add_text(
            text_content,
            dxfattribs={
                'height': wall_thickness / 4,  # Text height
                'layer': 'TEXT',  # Optional: specify a layer for the text
                'color': 7,
                # Optional: specify text color
                'insert': text_location,  # Position of the text
            }
        )
        leader_points = [
            (X11 + wall_thickness, overall_depth - y3 * 1.5),  # Start inside the rectangle
            (X11 + wall_thickness, 2 * overall_depth - y3),  # First bend point
            (X11 + 2 * wall_thickness, 2 * overall_depth - y3)  # End point at the text location
        ]

        msp.add_leader(leader_points, dxfattribs={
            'color': 7,
            'dimstyle': 'EZDXF'})
        # ----striupp

        X6 = clear_span * 1000
        Y6 = overall_depth
        text_content = f"Y-{stdia} Stirrups @ {max_spacing} c/c"
        text_location = (
            X6 / 3 - wall_thickness, -1 * overall_depth)  # Positioning the text outside the rectangle
        dimstyle = msp.doc.dimstyles.get('EZDXF')  # Get the 'Standard' DIMSTYLE or create a new one
        dimstyle.dxf.dimasz = nominal_cover * 3
        msp.add_text(
            text_content,
            dxfattribs={
                'height': wall_thickness / 4,  # Text height
                'layer': 'TEXT',  # Optional: specify a layer for the text
                'color': 7,
                # Optional: specify text color
                'insert': text_location,  # Position of the text
            }
        )
        leader_points = [
            (X6 / 2, Y6 / 2),  # Start inside the rectangle
            (X6 / 2 - wall_thickness, Y6 / 2),  # First bend point
            (X6 / 2 - wall_thickness, Y6 * -1)  # End point at the text location
        ]

        msp.add_leader(leader_points, dxfattribs={
            'color': 7,
            'dimstyle': 'EZDXF'})
        # a-a ytext end-----------------------------------------------
        # b-b text start----------------------------------------------------------
        text_content = f"{no_of_bars_bottom}-Y{main_bar} + 2-Y{main_bar}  "
        text_location = (
            clear_span * 500+wall_thickness  ,
            y4 - .55 * overall_depth)  # Positioning the text outside the rectangle
        dimstyle = msp.doc.dimstyles.get('EZDXF')  # Get the 'Standard' DIMSTYLE or create a new one
        dimstyle.dxf.dimasz = nominal_cover * 3
        msp.add_text(
            text_content,
            dxfattribs={
                'height': wall_thickness / 4,  # Text height
                'layer': 'TEXT',  # Optional: specify a layer for the text
                'color': 7,
                # Optional: specify text color
                'insert': text_location,  # Position of the text
            }
        )
        leader_points = [
            (clear_span * 500 , y4),  # Start inside the rectangle
            (clear_span * 500 , y4 - .5 * overall_depth),  # First bend point
            (clear_span * 500 +  wall_thickness, -.5 * overall_depth + y4)  # End point at the text location
        ]

        msp.add_leader(leader_points, dxfattribs={
            'color': 7,
            'dimstyle': 'EZDXF'})
        # -----top bar

        text_content = f"{no_of_bars_top}-Y{top_bar} "
        text_location = (
            clear_span * 500 +wall_thickness ,
            2.5 * overall_depth - y3 * 3)  # Positioning the text outside the rectangle
        dimstyle = msp.doc.dimstyles.get('EZDXF')  # Get the 'Standard' DIMSTYLE or create a new one
        dimstyle.dxf.dimasz = nominal_cover * 3
        msp.add_text(
            text_content,
            dxfattribs={
                'height': wall_thickness / 4,  # Text height
                'layer': 'TEXT',  # Optional: specify a layer for the text
                'color': 7,
                # Optional: specify text color
                'insert': text_location,  # Position of the text
            }
        )
        leader_points = [
            (clear_span * 500, overall_depth - y3 * 1.5),  # Start inside the rectangle
            (clear_span * 500 , 2 * overall_depth - y3),  # First bend point
            (clear_span * 500 +  wall_thickness, 2.5 * overall_depth - y3)  # End point at the text location
        ]

        msp.add_leader(leader_points, dxfattribs={
            'color': 7,
            'dimstyle': 'EZDXF'})
        # b-b- text end----------------------------------------------------------
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
        msp.add_line((500 * clear_span - nominal_cover-main_bar/100, -5 * overall_depth + nominal_cover),
                     (500 * clear_span - wall_thickness + nominal_cover+main_bar/100,
                      -5 * overall_depth + nominal_cover))  # bottom line
        msp.add_line((500 * clear_span - wall_thickness + nominal_cover, -5 * overall_depth + nominal_cover+main_bar/100),
                     (500 * clear_span - wall_thickness + nominal_cover,
                      -4 * overall_depth - nominal_cover-top_bar/100))  # left line
        msp.add_line((500 * clear_span - wall_thickness + nominal_cover+top_bar/100, -4 * overall_depth - nominal_cover),
                     (500 * clear_span - nominal_cover-top_bar/100, -4 * overall_depth - nominal_cover))
        msp.add_line((500 * clear_span - nominal_cover, -4 * overall_depth - nominal_cover-top_bar/100),
                     (500 * clear_span - nominal_cover, -5 * overall_depth + nominal_cover+main_bar/100))
        #text for stirru
        text_content = f"Y-{stdia} Stirrup @ {max_spacing} mm c/c"
        text_location = (500 * clear_span + nominal_cover + top_bar / 100, -4.45 * overall_depth - nominal_cover)  # Positioning the text outside the rectangle
        dimstyle = msp.doc.dimstyles.get('EZDXF')  # Get the 'Standard' DIMSTYLE or create a new one
        dimstyle.dxf.dimasz = nominal_cover * 3
        msp.add_text(
            text_content,
            dxfattribs={
                'height': .2,  # Text height
                'layer': 'TEXT',  # Optional: specify a layer for the text
                'color': 7,
                # Optional: specify text color
                'insert': text_location,  # Position of the text
            }
        )
        leader_points = [
            (500 * clear_span - wall_thickness + nominal_cover , -4.5 * overall_depth - nominal_cover),
            # Start inside the rectangle
            (500 * clear_span - wall_thickness+wall_thickness/2 , -4.4 * overall_depth - nominal_cover),
            # First bend point
            (500 * clear_span + nominal_cover + top_bar / 100, -4.4 * overall_depth - nominal_cover)
            # End point at the text location
        ]

        msp.add_leader(leader_points, dxfattribs={
            'color': 7,
            'dimstyle': 'EZDXF'})
        #hook b-b
        attribs = {'layer': '0', 'color': 7}

        startleft_point = (
        500 * clear_span - wall_thickness + nominal_cover, -5 * overall_depth + nominal_cover + main_bar / 100)
        endleft_point = (
        500 * clear_span - wall_thickness + nominal_cover + main_bar / 100, -5 * overall_depth + nominal_cover)
        arc2 = ConstructionArc.from_2p_radius(
            start_point=startleft_point,
            end_point=endleft_point,
            radius=main_bar / 100 + main_bar / 400  # left fillet
        )
        arc2.add_to_layout(msp, dxfattribs=attribs)
        startleft_point = (
            500 * clear_span - wall_thickness + nominal_cover, -5 * overall_depth + nominal_cover + main_bar / 100)
        endleft_point = (
            500 * clear_span - wall_thickness + nominal_cover + main_bar / 100, -5 * overall_depth + nominal_cover)
        # bottom left
        arc2 = ConstructionArc.from_2p_radius(
            start_point=startleft_point,
            end_point=endleft_point,
            radius=main_bar / 100 + main_bar / 400  # left fillet
        )
        arc2.add_to_layout(msp, dxfattribs=attribs)
        # bottom right-------------------------------------
        endleft_point1 = (500 * clear_span - nominal_cover, -5 * overall_depth + nominal_cover + main_bar / 100)
        startleft_point1 = (500 * clear_span - nominal_cover - main_bar / 100, -5 * overall_depth + nominal_cover)
        arc3 = ConstructionArc.from_2p_radius(
            start_point=startleft_point1,
            end_point=endleft_point1,
            radius=main_bar / 100 + main_bar / 400  # left fillet
        )
        arc3.add_to_layout(msp, dxfattribs=attribs)
        # top-left-----------------------------------------------------
        endleft_point2 = (500 * clear_span - nominal_cover - top_bar / 100, -4 * overall_depth - nominal_cover)
        startleft_point2 = (500 * clear_span - nominal_cover, -4 * overall_depth - nominal_cover - top_bar / 100)
        arc4 = ConstructionArc.from_2p_radius(
            start_point=startleft_point2,
            end_point=endleft_point2,
            radius=top_bar / 100  # left fillet
        )
        arc4.add_to_layout(msp, dxfattribs=attribs)
        # hook---------------------------------------
        msp.add_line(
            (500 * clear_span - wall_thickness + nominal_cover + top_bar / 100, -4 * overall_depth - nominal_cover), (
            500 * clear_span - wall_thickness + nominal_cover + top_bar / 100 + 2 * top_bar / 100,
            -4 * overall_depth - nominal_cover - 2 * top_bar / 100))
        msp.add_line(
            (500 * clear_span - wall_thickness + nominal_cover, -4 * overall_depth - nominal_cover - top_bar / 100), (
            500 * clear_span - wall_thickness + nominal_cover + 2 * top_bar / 100,
            -4 * overall_depth - nominal_cover - top_bar / 100 - 2 * top_bar / 100))
        # hook-fillet
        startleft_point3 = (
        500 * clear_span - wall_thickness + nominal_cover + top_bar / 100, -4 * overall_depth - nominal_cover)
        endleft_point3 = (
        500 * clear_span - wall_thickness + nominal_cover, -4 * overall_depth - nominal_cover - top_bar / 100)
        arc5 = ConstructionArc.from_2p_radius(
            start_point=startleft_point3,
            end_point=endleft_point3,
            radius=top_bar / 100  # left fillet
        )
        arc5.add_to_layout(msp, dxfattribs=attribs)

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
        insert_point = (1000 * clear_span-wall_thickness, -7 * overall_depth)  # X, Y coordinates where the text will be inserted.
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
        # section c-c
        msp.add_line((1000 * clear_span, -5 * overall_depth),
                     (1000 * clear_span - wall_thickness, -5 * overall_depth))  # bottom line
        msp.add_line((1000 * clear_span - wall_thickness, -5 * overall_depth),
                     (1000 * clear_span - wall_thickness, -4 * overall_depth))  # left line
        msp.add_line((1000 * clear_span - wall_thickness, -4 * overall_depth), (1000 * clear_span, -4 * overall_depth))
        msp.add_line((1000 * clear_span, -4 * overall_depth), (1000 * clear_span, -5 * overall_depth))
        # --stirrup cross
        nominal_cover = nominal_cover
        msp.add_line((1000 * clear_span - nominal_cover-main_bar/100, -5 * overall_depth + nominal_cover),
                     (1000 * clear_span - wall_thickness + nominal_cover+main_bar/100,
                      -5 * overall_depth + nominal_cover))  # bottom line
        msp.add_line(
            (1000 * clear_span - wall_thickness + nominal_cover, -5 * overall_depth + nominal_cover + main_bar / 100),
            (1000 * clear_span - wall_thickness + nominal_cover,
             -4 * overall_depth - nominal_cover - top_bar / 100))  # left line
        msp.add_line(
            (1000 * clear_span - wall_thickness + nominal_cover + top_bar / 100, -4 * overall_depth - nominal_cover),
            (1000 * clear_span - nominal_cover - top_bar / 100, -4 * overall_depth - nominal_cover))
        msp.add_line((1000 * clear_span - nominal_cover, -4 * overall_depth - nominal_cover-top_bar/100),
                     (1000 * clear_span - nominal_cover, -5 * overall_depth + nominal_cover+main_bar/100))#right line

        attribs = {'layer': '0', 'color': 7}

        startleft_point=( 1000 * clear_span - wall_thickness + nominal_cover, -5 * overall_depth + nominal_cover+main_bar/100 )
        endleft_point=(  1000 * clear_span - wall_thickness + nominal_cover +main_bar/100, -5 * overall_depth + nominal_cover)
        arc2=ConstructionArc.from_2p_radius(
            start_point=startleft_point,
            end_point=endleft_point,
            radius=main_bar/100+main_bar/400  # left fillet
         )
        arc2.add_to_layout(msp, dxfattribs=attribs)
        startleft_point = (
        1000 * clear_span - wall_thickness + nominal_cover, -5 * overall_depth + nominal_cover + main_bar / 100)
        endleft_point = (
        1000 * clear_span - wall_thickness + nominal_cover + main_bar / 100, -5 * overall_depth + nominal_cover)
        #bottom left
        arc2 = ConstructionArc.from_2p_radius(
            start_point=startleft_point,
            end_point=endleft_point,
            radius=main_bar / 100 + main_bar / 400  # left fillet
        )
        arc2.add_to_layout(msp, dxfattribs=attribs)
        #bottom right-------------------------------------
        endleft_point1 =(1000 * clear_span - nominal_cover, -5 * overall_depth + nominal_cover+main_bar/100)
        startleft_point1=(1000 * clear_span - nominal_cover-main_bar/100,-5 * overall_depth + nominal_cover)
        arc3 = ConstructionArc.from_2p_radius(
            start_point=startleft_point1,
            end_point=endleft_point1,
            radius=main_bar / 100 + main_bar / 400  # left fillet
        )
        arc3.add_to_layout(msp, dxfattribs=attribs)
        #top-left-----------------------------------------------------
        endleft_point2 = (1000 * clear_span - nominal_cover - top_bar / 100, -4 * overall_depth - nominal_cover)
        startleft_point2 = (1000 * clear_span - nominal_cover, -4 * overall_depth - nominal_cover-top_bar/100)
        arc4 = ConstructionArc.from_2p_radius(
            start_point=startleft_point2,
            end_point=endleft_point2,
            radius=top_bar/100  # left fillet
        )
        arc4.add_to_layout(msp, dxfattribs=attribs)
        #hook---------------------------------------
        text_content = f"Y-{stdia} Stirrup @ {max_spacing} mm c/c"
        text_location = (1000 * clear_span + nominal_cover + top_bar / 100,
                         -4.45 * overall_depth - nominal_cover)  # Positioning the text outside the rectangle
        dimstyle = msp.doc.dimstyles.get('EZDXF')  # Get the 'Standard' DIMSTYLE or create a new one
        dimstyle.dxf.dimasz = nominal_cover * 3
        msp.add_text(
            text_content,
            dxfattribs={
                'height': .2,  # Text height
                'layer': 'TEXT',  # Optional: specify a layer for the text
                'color': 7,
                # Optional: specify text color
                'insert': text_location,  # Position of the text
            }
        )
        leader_points = [
            (1000 * clear_span - wall_thickness + nominal_cover, -4.5 * overall_depth - nominal_cover),
            # Start inside the rectangle
            (1000 * clear_span - wall_thickness + wall_thickness / 2, -4.4 * overall_depth - nominal_cover),
            # First bend point
            (1000 * clear_span + nominal_cover + top_bar / 100, -4.4 * overall_depth - nominal_cover)
            # End point at the text location
        ]

        msp.add_leader(leader_points, dxfattribs={
            'color': 7,
            'dimstyle': 'EZDXF'})
        msp.add_line((1000 * clear_span - wall_thickness + nominal_cover + top_bar / 100, -4 * overall_depth - nominal_cover),(1000 * clear_span - wall_thickness + nominal_cover + top_bar / 100+2*top_bar/100,-4 * overall_depth - nominal_cover-2*top_bar/100))
        msp.add_line((1000 * clear_span - wall_thickness + nominal_cover, -4 * overall_depth - nominal_cover - top_bar / 100),(1000 * clear_span - wall_thickness + nominal_cover+2*top_bar/100, -4 * overall_depth - nominal_cover - top_bar / 100-2*top_bar/100))
        #hook-fillet
        startleft_point3 =(1000 * clear_span - wall_thickness + nominal_cover + top_bar / 100, -4 * overall_depth - nominal_cover)
        endleft_point3= (1000 * clear_span - wall_thickness + nominal_cover, -4 * overall_depth - nominal_cover - top_bar / 100)
        arc5 = ConstructionArc.from_2p_radius(
            start_point=startleft_point3,
            end_point=endleft_point3,
            radius=top_bar/100  # left fillet
        )
        arc5.add_to_layout(msp, dxfattribs=attribs)



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
        #-----------------------------------------------------------------BBS---------------------------------------------

        start_x = 0
        start_y = -8*o_d/100
        cell_width = wall_thickness*3
        cell_height = wall_thickness
        header_height = 2*wall_thickness
        print('bbs-------------------------------------------------------------------------------------------------------------------------------------------')
        #-----------------------cutting lenth top bar---------------------------
        cut_top_bar=round(clear_span*100000+2*50*top_bar -2*nominal_cover*100,3)
        cut_bot_bar=round(clear_span*100000+2*50*main_bar -2*nominal_cover*100,3)
        print(cut_top_bar)
        print(cut_bot_bar)
        print(no_of_bars_top)
        #bar shape text--------------------------------------------------------
        bar_string = "a"
        insert_point = (
            2* cell_width*.9 , start_y - cell_height*2.5 )  # X, Y coordinates where the text will be inserted.
        text_height = .5
        # Add text to the modelspace.
        msp.add_text(
            bar_string,
            dxfattribs={
                'insert': insert_point,
                'height': text_height,
                # Additional attributes such as font, rotation, and color can be specified here.
                'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                'rotation': 0,
                'color': 7
            }
        )
        bar_string = "b"
        insert_point = (
            1.5 * cell_width , start_y - cell_height * 2.5)  # X, Y coordinates where the text will be inserted.
        text_height = .5
        # Add text to the modelspace.
        msp.add_text(
            bar_string,
            dxfattribs={
                'insert': insert_point,
                'height': text_height,
                # Additional attributes such as font, rotation, and color can be specified here.
                'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                'rotation': 0,
                'color': 7
            }
        )
        bar_string = "Top Bar"
        insert_point = (
              .1*cell_width, start_y - cell_height * 2.5)  # X, Y coordinates where the text will be inserted.
        text_height = .5
        # Add text to the modelspace.
        msp.add_text(
            bar_string,
            dxfattribs={
                'insert': insert_point,
                'height': text_height,
                # Additional attributes such as font, rotation, and color can be specified here.
                'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                'rotation': 0,
                'color': 7
            }
        )
        a_top=50*top_bar
        bar_string = str(a_top/1000)
        insert_point = (
            2.5*cell_width, start_y - cell_height * 2.5)  # X, Y coordinates where the text will be inserted.
        text_height = .5
        # Add text to the modelspace.
        msp.add_text(
            bar_string,
            dxfattribs={
                'insert': insert_point,
                'height': text_height,
                # Additional attributes such as font, rotation, and color can be specified here.
                'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                'rotation': 0,
                'color': 7
            }
        )

        bar_string = "Nil"
        insert_point = (
            4.5 * cell_width, start_y - cell_height * 2.5)  # X, Y coordinates where the text will be inserted.
        text_height = .5
        # Add text to the modelspace.
        msp.add_text(
            bar_string,
            dxfattribs={
                'insert': insert_point,
                'height': text_height,
                # Additional attributes such as font, rotation, and color can be specified here.
                'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                'rotation': 0,
                'color': 7
            }
        )
        b_top = clear_span * 100
        bar_string = str(b_top)
        insert_point = (
            3.5 * cell_width, start_y - cell_height * 2.5)  # X, Y coordinates where the text will be inserted.
        text_height = .5
        # Add text to the modelspace.
        msp.add_text(
            bar_string,
            dxfattribs={
                'insert': insert_point,
                'height': text_height,
                # Additional attributes such as font, rotation, and color can be specified here.
                'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                'rotation': 0,
                'color': 7
            }
        )
        b_top = top_bar
        bar_string = str(b_top)
        insert_point = (
            5.5 * cell_width, start_y - cell_height * 2.5)  # X, Y coordinates where the text will be inserted.
        text_height = .5
        # Add text to the modelspace.
        msp.add_text(
            bar_string,
            dxfattribs={
                'insert': insert_point,
                'height': text_height,
                # Additional attributes such as font, rotation, and color can be specified here.
                'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                'rotation': 0,
                'color': 7
            }
        )
        bar_string = "Nil"
        insert_point = (
            6.5 * cell_width, start_y - cell_height * 2.5)  # X, Y coordinates where the text will be inserted.
        text_height = .5
        # Add text to the modelspace.
        msp.add_text(
            bar_string,
            dxfattribs={
                'insert': insert_point,
                'height': text_height,
                # Additional attributes such as font, rotation, and color can be specified here.
                'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                'rotation': 0,
                'color': 7
            }
        )
        #row 1 end---------------------------------------------------------------------------------------------------------------------------------------------row-1 end
        #row2------------------------row -2 -------------------------------------------------- row -2
        bar_string = "a"
        insert_point = (
            2 * cell_width * .95, start_y - cell_height * 3.6)  # X, Y coordinates where the text will be inserted.
        text_height = .5
        # Add text to the modelspace.
        msp.add_text(
            bar_string,
            dxfattribs={
                'insert': insert_point,
                'height': text_height,
                # Additional attributes such as font, rotation, and color can be specified here.
                'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                'rotation': 0,
                'color': 7
            }
        )
        bar_string = "b"
        insert_point = (
            1.5 * cell_width, start_y - cell_height * 3.5)  # X, Y coordinates where the text will be inserted.
        text_height = .5
        # Add text to the modelspace.
        msp.add_text(
            bar_string,
            dxfattribs={
                'insert': insert_point,
                'height': text_height,
                # Additional attributes such as font, rotation, and color can be specified here.
                'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                'rotation': 0,
                'color': 7
            }
        )
        bar_string = "Bottom Bar"
        insert_point = (
            .1*cell_width, start_y - cell_height * 3.5)  # X, Y coordinates where the text will be inserted.
        text_height = .5
        # Add text to the modelspace.
        msp.add_text(
            bar_string,
            dxfattribs={
                'insert': insert_point,
                'height': text_height,
                # Additional attributes such as font, rotation, and color can be specified here.
                'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                'rotation': 0,
                'color': 7
            }
        )
        a_top = 50 * main_bar
        bar_string = str(a_top / 1000)
        insert_point = (
            2.5 * cell_width, start_y - cell_height * 3.5)  # X, Y coordinates where the text will be inserted.
        text_height = .5
        # Add text to the modelspace.
        msp.add_text(
            bar_string,
            dxfattribs={
                'insert': insert_point,
                'height': text_height,
                # Additional attributes such as font, rotation, and color can be specified here.
                'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                'rotation': 0,
                'color': 7
            }
        )

        bar_string = "Nil"
        insert_point = (
            4.5 * cell_width, start_y - cell_height * 3.5)  # X, Y coordinates where the text will be inserted.
        text_height = .5
        # Add text to the modelspace.
        msp.add_text(
            bar_string,
            dxfattribs={
                'insert': insert_point,
                'height': text_height,
                # Additional attributes such as font, rotation, and color can be specified here.
                'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                'rotation': 0,
                'color': 7
            }
        )
        b_top = clear_span * 100
        bar_string = str(b_top)
        insert_point = (
            3.5 * cell_width, start_y - cell_height * 3.5)  # X, Y coordinates where the text will be inserted.
        text_height = .5
        # Add text to the modelspace.
        msp.add_text(
            bar_string,
            dxfattribs={
                'insert': insert_point,
                'height': text_height,
                # Additional attributes such as font, rotation, and color can be specified here.
                'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                'rotation': 0,
                'color': 7
            }
        )
        b_top = main_bar
        bar_string = str(b_top)
        insert_point = (
            5.5 * cell_width, start_y - cell_height * 3.5)  # X, Y coordinates where the text will be inserted.
        text_height = .5
        # Add text to the modelspace.
        msp.add_text(
            bar_string,
            dxfattribs={
                'insert': insert_point,
                'height': text_height,
                # Additional attributes such as font, rotation, and color can be specified here.
                'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                'rotation': 0,
                'color': 7
            }
        )
        bar_string = "Nil"
        insert_point = (
            6.5 * cell_width, start_y - cell_height * 3.5)  # X, Y coordinates where the text will be inserted.
        text_height = .5
        # Add text to the modelspace.
        msp.add_text(
            bar_string,
            dxfattribs={
                'insert': insert_point,
                'height': text_height,
                # Additional attributes such as font, rotation, and color can be specified here.
                'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                'rotation': 0,
                'color': 7
            }
        )
        #text insert for cutting length top-----------------------------
        top_string = str(cut_top_bar/1000)
        insert_point = (7*cell_width+.8, start_y-cell_height*3+.5)  # X, Y coordinates where the text will be inserted.
        text_height = 1
        # Add text to the modelspace.
        msp.add_text(
            top_string,
            dxfattribs={
                'insert': insert_point,
                'height': text_height,
                # Additional attributes such as font, rotation, and color can be specified here.
                'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                'rotation': 0,
                'color': 7
            }
        )
        #number of bars ---------------------------------------------------

        top_string = str(no_of_bars_top)
        insert_point = (
        8 * cell_width + .8, start_y - cell_height*3+.5)  # X, Y coordinates where the text will be inserted.
        text_height = 1
        # Add text to the modelspace.
        msp.add_text(
            top_string,
            dxfattribs={
                'insert': insert_point,
                'height': text_height,
                # Additional attributes such as font, rotation, and color can be specified here.
                'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                'rotation': 0,
                'color': 7
            }
        )
        #striupp-----------------------------------------------------------------------------------------------------
        bar_string = "c"
        insert_point = (
            2 * cell_width * .6, start_y - cell_height * 4.6)  # X, Y coordinates where the text will be inserted.
        text_height = .5
        # Add text to the modelspace.
        msp.add_text(
            bar_string,
            dxfattribs={
                'insert': insert_point,
                'height': text_height,
                # Additional attributes such as font, rotation, and color can be specified here.
                'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                'rotation': 0,
                'color': 7
            }
        )
        bar_string = "a"
        insert_point = (
            1.5 * cell_width, start_y - cell_height * 4.5)  # X, Y coordinates where the text will be inserted.
        text_height = .5
        # Add text to the modelspace.
        msp.add_text(
            bar_string,
            dxfattribs={
                'insert': insert_point,
                'height': text_height,
                # Additional attributes such as font, rotation, and color can be specified here.
                'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                'rotation': 0,
                'color': 7
            }
        )
        bar_string = "Stirrup"
        insert_point = (
            .1*cell_width  ,start_y - cell_height * 4.5)  # X, Y coordinates where the text will be inserted.
        text_height = .5
        # Add text to the modelspace.
        msp.add_text(
            bar_string,
            dxfattribs={
                'insert': insert_point,
                'height': text_height,
                # Additional attributes such as font, rotation, and color can be specified here.
                'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                'rotation': 0,
                'color': 7
            }
        )
        a_top = round(wall_thickness*100-200*nominal_cover,3)
        print("wall",wall_thickness)
        bar_string = str(a_top / 1000)
        insert_point = (
            2.5 * cell_width, start_y - cell_height * 4.5)  # X, Y coordinates where the text will be inserted.
        text_height = .5
        # Add text to the modelspace.
        msp.add_text(
            bar_string,
            dxfattribs={
                'insert': insert_point,
                'height': text_height,
                # Additional attributes such as font, rotation, and color can be specified here.
                'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                'rotation': 0,
                'color': 7
            }
        )
        st_dep=o_d-200*nominal_cover
        bar_string = str(st_dep/1000)
        insert_point = (
            4.5 * cell_width, start_y - cell_height * 4.5)  # X, Y coordinates where the text will be inserted.
        text_height = .5
        # Add text to the modelspace.
        msp.add_text(
            bar_string,
            dxfattribs={
                'insert': insert_point,
                'height': text_height,
                # Additional attributes such as font, rotation, and color can be specified here.
                'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                'rotation': 0,
                'color': 7
            }
        )

        bar_string = "Nil"
        insert_point = (
            3.5 * cell_width, start_y - cell_height * 4.5)  # X, Y coordinates where the text will be inserted.
        text_height = .5
        # Add text to the modelspace.
        msp.add_text(
            bar_string,
            dxfattribs={
                'insert': insert_point,
                'height': text_height,
                # Additional attributes such as font, rotation, and color can be specified here.
                'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                'rotation': 0,
                'color': 7
            }
        )
        b_top = stdia
        bar_string = str(b_top)
        insert_point = (
            5.5 * cell_width, start_y - cell_height * 4.5)  # X, Y coordinates where the text will be inserted.
        text_height = .5
        # Add text to the modelspace.
        msp.add_text(
            bar_string,
            dxfattribs={
                'insert': insert_point,
                'height': text_height,
                # Additional attributes such as font, rotation, and color can be specified here.
                'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                'rotation': 0,
                'color': 7
            }
        )
        b_top = round(2*(10*stdia/1000+st_dep/1000+a_top / 1000-3*stdia/1000)-3*stdia/1000,3)
        stirrup_cut_length=b_top
        bar_string = str(b_top)
        insert_point = (
            7 * cell_width+1, start_y - cell_height * 5+.5)  # X, Y coordinates where the text will be inserted.
        text_height = 1
        # Add text to the modelspace.
        msp.add_text(
            bar_string,
            dxfattribs={
                'insert': insert_point,
                'height': text_height,
                # Additional attributes such as font, rotation, and color can be specified here.
                'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                'rotation': 0,
                'color': 7
            }
        )
        bar_string = str(max_spacing)
        insert_point = (
            6.5 * cell_width, start_y - cell_height * 4.5)  # X, Y coordinates where the text will be inserted.
        text_height = .5
        # Add text to the modelspace.
        msp.add_text(
            bar_string,
            dxfattribs={
                'insert': insert_point,
                'height': text_height,
                # Additional attributes such as font, rotation, and color can be specified here.
                'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                'rotation': 0,
                'color': 7
            }
        )
        no_str = math.ceil(clear_span * 100000 / max_spacing + 1)

        top_string = str(no_str)
        insert_point = (
            8 * cell_width + .8, start_y - cell_height * 5 + .5)  # X, Y coordinates where the text will be inserted.
        text_height = 1
        # Add text to the modelspace.
        msp.add_text(
            top_string,
            dxfattribs={
                'insert': insert_point,
                'height': text_height,
                # Additional attributes such as font, rotation, and color can be specified here.
                'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                'rotation': 0,
                'color': 7
            }
        )
        #stirru shape------------------------------------------------------------
        msp.add_line((1.3 * cell_width, start_y - cell_height * 5 + .5),(1.6 * cell_width, start_y - cell_height * 5 + .5))
        msp.add_line((1.3 * cell_width, start_y - cell_height * 4.5 + .5),(1.3 * cell_width, start_y - cell_height * 5 + .5))
        msp.add_line((1.6 * cell_width, start_y - cell_height * 4.5 + .5),(1.6 * cell_width, start_y - cell_height * 5 + .5))
        msp.add_line((1.3 * cell_width, start_y - cell_height * 4.5 + .5),(1.6 * cell_width, start_y - cell_height * 4.5 + .5))
        #hook--------------------------------------------------------------------------------------
        msp.add_line((1.3 * cell_width, start_y - cell_height * 4.5 + .45),(1.3*cell_width+.4,start_y-cell_height*4.5-.25))
        msp.add_line((1.3 * cell_width+.4, start_y - cell_height * 4.5 + .5),
                     (1.3 * cell_width+.8 , start_y - cell_height * 4.5 ))
        # striupp end
        #dia with total length-----------------------------------------------------------------------------------------------------------------------

        # text insert for cutting length top-----------------------------
        top_string = str(cut_top_bar / 1000)
        cut_length_top=cut_top_bar / 1000
        insert_point = (
        7 * cell_width + .8, start_y - cell_height * 3 + .5)  # X, Y coordinates where the text will be inserted.
        text_height = 1
        # Add text to the modelspace.
        msp.add_text(
            top_string,
            dxfattribs={
                'insert': insert_point,
                'height': text_height,
                # Additional attributes such as font, rotation, and color can be specified here.
                'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                'rotation': 0,
                'color': 7
            }
        )
        # number of bars ---------------------------------------------------
        top_string = str(no_of_bars_top)
        print("t",no_of_bars_top)
        insert_point = (
            8 * cell_width + .8, start_y - cell_height * 3 + .5)  # X, Y coordinates where the text will be inserted.
        text_height = 1
        # Add text to the modelspace.
        msp.add_text(
            top_string,
            dxfattribs={
                'insert': insert_point,
                'height': text_height,
                # Additional attributes such as font, rotation, and color can be specified here.
                'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                'rotation': 0,
                'color': 7
            }
        )

        #bottom bar-------------------------------------------------------------------------------
        msp.add_line((1.2*cell_width,start_y - cell_height*4 +.5),(1.8*cell_width,start_y - cell_height*4 +.5))
        msp.add_line((1.2 * cell_width, start_y - cell_height * 3.5 + .5),
                     (1.2 * cell_width, start_y - cell_height * 4 + .5))
        msp.add_line((1.8 * cell_width, start_y - cell_height * 3.5 + .5),
                     (1.8 * cell_width, start_y - cell_height * 4 + .5))
        bot_string = str(cut_bot_bar / 1000)
        cut_length_bottom=cut_bot_bar / 1000
        insert_point = (
        7 * cell_width + .8, start_y - cell_height*4 +.5)  # X, Y coordinates where the text will be inserted.
        text_height = 1
        # Add text to the modelspace.
        msp.add_text(
            bot_string,
            dxfattribs={
                'insert': insert_point,
                'height': text_height,
                # Additional attributes such as font, rotation, and color can be specified here.
                'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                'rotation': 0,
                'color': 7
            }
        )
        #number of bottom bars
        bot_string = str(no_of_bars_bottom )
        insert_point = (
            8 * cell_width + .8, start_y - cell_height*4+.5)  # X, Y coordinates where the text will be inserted.
        text_height = 1
        # Add text to the modelspace.
        msp.add_text(
            bot_string,
            dxfattribs={
                'insert': insert_point,
                'height': text_height,
                # Additional attributes such as font, rotation, and color can be specified here.
                'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                'rotation': 0,
                'color': 7
            }
        )

        # Column headers
        msp.add_line((9*cell_width,start_y),(9*cell_width,start_y+cell_height))
        msp.add_line((17 * cell_width, start_y), (17 * cell_width, start_y + cell_height))
        msp.add_line((9*cell_width,start_y+cell_height),(17 * cell_width, start_y + cell_height))
        #weight calculation----------------------------------------------------------------------------------

        msp.add_line((9 * cell_width, start_y - 10 * cell_height), (9 * cell_width, start_y - 5 * cell_height))
        msp.add_line((10 * cell_width, start_y - 9 * cell_height), (10 * cell_width, start_y - 5 * cell_height))
        msp.add_line((11 * cell_width, start_y - 9 * cell_height), (11 * cell_width, start_y - 5 * cell_height))
        msp.add_line((12 * cell_width, start_y - 9 * cell_height), (12 * cell_width, start_y - 5 * cell_height))
        msp.add_line((13 * cell_width, start_y - 9 * cell_height), (13* cell_width, start_y - 5 * cell_height))
        msp.add_line((14 * cell_width, start_y - 9 * cell_height), (14 * cell_width, start_y - 5 * cell_height))
        msp.add_line((15 * cell_width, start_y - 9 * cell_height), (15 * cell_width, start_y - 5 * cell_height))
        msp.add_line((16 * cell_width, start_y - 9 * cell_height), (16 * cell_width, start_y - 5 * cell_height))
        msp.add_line((17 * cell_width, start_y - 10 * cell_height), (17 * cell_width, start_y - 5 * cell_height))
        msp.add_line((6 * cell_width, start_y-10*cell_height), ( 6* cell_width, start_y- 5* cell_height))
        msp.add_line((17 * cell_width, start_y - 9 * cell_height), (17 * cell_width, start_y - 5 * cell_height))
        msp.add_line(( 6* cell_width, start_y- 10* cell_height), (17 * cell_width, start_y - 10 * cell_height))
        bot_string = "Total reinforcement Weight in Kg's"
        insert_point = ( 6.1* cell_width, start_y- 9.5* cell_height) # X, Y coordinates where the text will be inserted.
        text_height = .8
        # Add text to the modelspace.
        msp.add_text(
            bot_string,
            dxfattribs={
                'insert': insert_point,
                'height': text_height,
                # Additional attributes such as font, rotation, and color can be specified here.
                'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                'rotation': 0,
                'color': 7
            }
        )
        msp.add_line((6 * cell_width, start_y - 9 * cell_height), (17 * cell_width, start_y - 9 * cell_height))
        bot_string = " Weight in Kg's"
        insert_point = (
        6.1 * cell_width, start_y - 8.5 * cell_height)  # X, Y coordinates where the text will be inserted.
        text_height = .8
        # Add text to the modelspace.
        msp.add_text(
            bot_string,
            dxfattribs={
                'insert': insert_point,
                'height': text_height,
                # Additional attributes such as font, rotation, and color can be specified here.
                'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                'rotation': 0,
                'color': 7
            }
        )
        msp.add_line((6 * cell_width, start_y - 8 * cell_height), (17 * cell_width, start_y - 8 * cell_height))
        bot_string = "Unit Weight in Kg/m"
        insert_point = (
        6.1 * cell_width, start_y - 7.5 * cell_height)  # X, Y coordinates where the text will be inserted.
        text_height = .8
        # Add text to the modelspace.
        msp.add_text(
            bot_string,
            dxfattribs={
                'insert': insert_point,
                'height': text_height,
                # Additional attributes such as font, rotation, and color can be specified here.
                'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                'rotation': 0,
                'color': 7
            }
        )
        msp.add_line((6 * cell_width, start_y - 7 * cell_height), (17 * cell_width, start_y - 7 * cell_height))
        bot_string = "Total length (m)"
        insert_point = (
        6.1 * cell_width, start_y - 6.5 * cell_height)  # X, Y coordinates where the text will be inserted.
        text_height = .8
        # Add text to the modelspace.
        msp.add_text(
            bot_string,
            dxfattribs={
                'insert': insert_point,
                'height': text_height,
                # Additional attributes such as font, rotation, and color can be specified here.
                'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                'rotation': 0,
                'color': 7
            }
        )
        st_length = round(stirrup_cut_length * no_str, 3)
        dia_string = str(st_length)
        insert_point = (
            9.1 * cell_width ,
            start_y - cell_height * 6.9)  # X, Y coordinates where the text will be inserted.
        text_height = 1
        # Add text to the modelspace.
        msp.add_text(
            dia_string,
            dxfattribs={
                'insert': insert_point,
                'height': text_height,
                # Additional attributes such as font, rotation, and color can be specified here.
                'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                'rotation': 0,
                'color': 7
            }
        )
        if(top_bar==12 and main_bar==12):
            bot_length = round(cut_length_bottom * no_bars_bottom, 3) + round(cut_length_top*no_of_bars_top,3)
            dia_string = str(round(bot_length,3))
            insert_point = (
                11.1 * cell_width ,
                start_y - cell_height *6.9)  # X, Y coordinates where the text will be inserted.
            text_height = 1
            # Add text to the modelspace.
            msp.add_text(
                dia_string,
                dxfattribs={
                    'insert': insert_point,
                    'height': text_height,
                    # Additional attributes such as font, rotation, and color can be specified here.
                    'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                    'rotation': 0,
                    'color': 7
                }
            )
            bot_length = round(cut_length_bottom * no_bars_bottom, 3) + round(cut_length_top * no_of_bars_top, 3)
            dia_string = str(round(bot_length*.889,3))
            insert_point = (
                11.1 * cell_width,
                start_y - cell_height * 8.9)  # X, Y coordinates where the text will be inserted.
            text_height = 1
            # Add text to the modelspace.
            msp.add_text(
                dia_string,
                dxfattribs={
                    'insert': insert_point,
                    'height': text_height,
                    # Additional attributes such as font, rotation, and color can be specified here.
                    'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                    'rotation': 0,
                    'color': 7
                }
            )
        if (top_bar == 16 and main_bar == 16):
            bot_length = round(cut_length_bottom * no_bars_bottom, 3) + round(cut_length_top * no_of_bars_top, 3)
            dia_string = str(round(bot_length,3))
            insert_point = (
                12.1 * cell_width,
                start_y - cell_height * 6.9)  # X, Y coordinates where the text will be inserted.
            text_height = 1
            # Add text to the modelspace.
            msp.add_text(
                dia_string,
                dxfattribs={
                    'insert': insert_point,
                    'height': text_height,
                    # Additional attributes such as font, rotation, and color can be specified here.
                    'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                    'rotation': 0,
                    'color': 7
                }
            )
            bot_length = round(cut_length_bottom * no_bars_bottom, 3) + round(cut_length_top * no_of_bars_top, 3)
            dia_string = str(round(bot_length*1.578,))
            insert_point = (
                12.1 * cell_width,
                start_y - cell_height * 8.9)  # X, Y coordinates where the text will be inserted.
            text_height = 1
            # Add text to the modelspace.
            msp.add_text(
                dia_string,
                dxfattribs={
                    'insert': insert_point,
                    'height': text_height,
                    # Additional attributes such as font, rotation, and color can be specified here.
                    'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                    'rotation': 0,
                    'color': 7
                }
            )
        if (top_bar == 20 and main_bar == 20):
            bot_length = round(cut_length_bottom * no_bars_bottom, 3) + round(cut_length_top * no_of_bars_top, 3)
            dia_string = str(round(bot_length,3))
            insert_point = (
                13.1 * cell_width,
                start_y - cell_height * 6.9)  # X, Y coordinates where the text will be inserted.
            text_height = 1
            # Add text to the modelspace.
            msp.add_text(
                dia_string,
                dxfattribs={
                    'insert': insert_point,
                    'height': text_height,
                    # Additional attributes such as font, rotation, and color can be specified here.
                    'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                    'rotation': 0,
                    'color': 7
                }
            )
            bot_length = round(cut_length_bottom * no_bars_bottom, 3) + round(cut_length_top * no_of_bars_top, 3)
            dia_string = str(round(bot_length*2.469,3))
            insert_point = (
                13.1 * cell_width,
                start_y - cell_height * 8.9)  # X, Y coordinates where the text will be inserted.
            text_height = 1
            # Add text to the modelspace.
            msp.add_text(
                dia_string,
                dxfattribs={
                    'insert': insert_point,
                    'height': text_height,
                    # Additional attributes such as font, rotation, and color can be specified here.
                    'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                    'rotation': 0,
                    'color': 7
                }
            )
        if (top_bar == 25 and main_bar == 25):
            bot_length = round(cut_length_bottom * no_bars_bottom, 3) + round(cut_length_top * no_of_bars_top, 3)
            dia_string = str(round(bot_length,3))
            insert_point = (
                14.1 * cell_width,
                start_y - cell_height * 6.9)  # X, Y coordinates where the text will be inserted.
            text_height = 1
            # Add text to the modelspace.
            msp.add_text(
                dia_string,
                dxfattribs={
                    'insert': insert_point,
                    'height': text_height,
                    # Additional attributes such as font, rotation, and color can be specified here.
                    'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                    'rotation': 0,
                    'color': 7
                }
            )
            bot_length = round(cut_length_bottom * no_bars_bottom, 3) + round(cut_length_top * no_of_bars_top, 3)
            dia_string = str(round(bot_length*3.858,3))
            insert_point = (
                14.1 * cell_width,
                start_y - cell_height * 8.9)  # X, Y coordinates where the text will be inserted.
            text_height = 1
            # Add text to the modelspace.
            msp.add_text(
                dia_string,
                dxfattribs={
                    'insert': insert_point,
                    'height': text_height,
                    # Additional attributes such as font, rotation, and color can be specified here.
                    'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                    'rotation': 0,
                    'color': 7
                }
            )
        if (top_bar == 32 and main_bar == 32):
            bot_length = round(cut_length_bottom * no_bars_bottom, 3) + round(cut_length_top * no_of_bars_top, 3)
            dia_string = str(round(bot_length,3))
            insert_point = (
                15.1 * cell_width,
                start_y - cell_height * 6.9)  # X, Y coordinates where the text will be inserted.
            text_height = 1
            # Add text to the modelspace.
            msp.add_text(
                dia_string,
                dxfattribs={
                    'insert': insert_point,
                    'height': text_height,
                    # Additional attributes such as font, rotation, and color can be specified here.
                    'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                    'rotation': 0,
                    'color': 7
                }
            )
            bot_length = round(cut_length_bottom * no_bars_bottom, 3) + round(cut_length_top * no_of_bars_top, 3)
            dia_string = str(round(bot_length*6.321,3))
            insert_point = (
                15.1 * cell_width,
                start_y - cell_height * 8.9)  # X, Y coordinates where the text will be inserted.
            text_height = 1
            # Add text to the modelspace.
            msp.add_text(
                dia_string,
                dxfattribs={
                    'insert': insert_point,
                    'height': text_height,
                    # Additional attributes such as font, rotation, and color can be specified here.
                    'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                    'rotation': 0,
                    'color': 7
                }
            )
        if (top_bar == 40 and main_bar == 40):
            bot_length = round(cut_length_bottom * no_bars_bottom, 3) + round(cut_length_top * no_of_bars_top, 3)
            dia_string = str(round(bot_length,3))
            insert_point = (
                16.1 * cell_width,
                start_y - cell_height * 6.9)  # X, Y coordinates where the text will be inserted.
            text_height = 1
            # Add text to the modelspace.
            msp.add_text(
                dia_string,
                dxfattribs={
                    'insert': insert_point,
                    'height': text_height,
                    # Additional attributes such as font, rotation, and color can be specified here.
                    'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                    'rotation': 0,
                    'color': 7
                }
            )
            bot_length = round(cut_length_bottom * no_bars_bottom, 3) + round(cut_length_top * no_of_bars_top, 3)
            dia_string = str(round(bot_length*9.877,3))
            insert_point = (
                16.1 * cell_width,
                start_y - cell_height * 8.9)  # X, Y coordinates where the text will be inserted.
            text_height = 1
            # Add text to the modelspace.
            msp.add_text(
                dia_string,
                dxfattribs={
                    'insert': insert_point,
                    'height': text_height,
                    # Additional attributes such as font, rotation, and color can be specified here.
                    'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                    'rotation': 0,
                    'color': 7
                }
            )
        if (top_bar == 12 and main_bar != 12):
            bot_length =  round(cut_length_top * no_of_bars_top, 3)

            dia_string = str(round(bot_length, 3))
            insert_point = (
                11.1 * cell_width,
                start_y - cell_height * 6.9)  # X, Y coordinates where the text will be inserted.
            text_height = 1
            # Add text to the modelspace.
            msp.add_text(
                dia_string,
                dxfattribs={
                    'insert': insert_point,
                    'height': text_height,
                    # Additional attributes such as font, rotation, and color can be specified here.
                    'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                    'rotation': 0,
                    'color': 7
                }
            )
            bot_length = round(cut_length_top * no_of_bars_top, 3)
            dia_string = str(round(bot_length*.889,3))
            insert_point = (
                11.1 * cell_width,
                start_y - cell_height * 8.9)  # X, Y coordinates where the text will be inserted.
            text_height = 1
            # Add text to the modelspace.
            msp.add_text(
                dia_string,
                dxfattribs={
                    'insert': insert_point,
                    'height': text_height,
                    # Additional attributes such as font, rotation, and color can be specified here.
                    'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                    'rotation': 0,
                    'color': 7
                }
            )
        if (top_bar == 16 and main_bar != 16):
            bot_length = round(cut_length_top * no_of_bars_top, 3)
            dia_string = str(round(bot_length,3))
            insert_point = (
                12.1 * cell_width,
                start_y - cell_height * 6.9)  # X, Y coordinates where the text will be inserted.
            text_height = 1
            # Add text to the modelspace.
            msp.add_text(
                dia_string,
                dxfattribs={
                    'insert': insert_point,
                    'height': text_height,
                    # Additional attributes such as font, rotation, and color can be specified here.
                    'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                    'rotation': 0,
                    'color': 7
                }
            )
            bot_length = round(cut_length_top * no_of_bars_top, 3)
            dia_string = str(round(bot_length*1.58  , 3))
            insert_point = (
                12.1 * cell_width,
                start_y - cell_height * 8.9)  # X, Y coordinates where the text will be inserted.
            text_height = 1
            # Add text to the modelspace.
            msp.add_text(
                dia_string,
                dxfattribs={
                    'insert': insert_point,
                    'height': text_height,
                    # Additional attributes such as font, rotation, and color can be specified here.
                    'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                    'rotation': 0,
                    'color': 7
                }
            )
        if (top_bar == 20 and main_bar != 20):
            bot_length = round(cut_length_top * no_of_bars_top, 3)
            dia_string = str(round(bot_length,3))
            insert_point = (
                13.1 * cell_width,
                start_y - cell_height * 6.9)  # X, Y coordinates where the text will be inserted.
            text_height = 1
            # Add text to the modelspace.
            msp.add_text(
                dia_string,
                dxfattribs={
                    'insert': insert_point,
                    'height': text_height,
                    # Additional attributes such as font, rotation, and color can be specified here.
                    'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                    'rotation': 0,
                    'color': 7
                }
            )
            bot_length = round(cut_length_top * no_of_bars_top, 3)
            dia_string = str(round(bot_length*2.469,3))
            insert_point = (
                13.1 * cell_width,
                start_y - cell_height * 8.9)  # X, Y coordinates where the text will be inserted.
            text_height = 1
            # Add text to the modelspace.
            msp.add_text(
                dia_string,
                dxfattribs={
                    'insert': insert_point,
                    'height': text_height,
                    # Additional attributes such as font, rotation, and color can be specified here.
                    'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                    'rotation': 0,
                    'color': 7
                }
            )
        if (top_bar == 25 and main_bar != 25):
            bot_length =  round(cut_length_top * no_of_bars_top, 3)
            dia_string = str(round(bot_length,3))
            insert_point = (
                14.1 * cell_width,
                start_y - cell_height * 6.9)  # X, Y coordinates where the text will be inserted.
            text_height = 1
            # Add text to the modelspace.
            msp.add_text(
                dia_string,
                dxfattribs={
                    'insert': insert_point,
                    'height': text_height,
                    # Additional attributes such as font, rotation, and color can be specified here.
                    'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                    'rotation': 0,
                    'color': 7
                }
            )
            bot_length = round(cut_length_top * no_of_bars_top, 3)
            dia_string = str(round(bot_length*3.858,3))
            insert_point = (
                14.1 * cell_width,
                start_y - cell_height * 8.9)  # X, Y coordinates where the text will be inserted.
            text_height = 1
            # Add text to the modelspace.
            msp.add_text(
                dia_string,
                dxfattribs={
                    'insert': insert_point,
                    'height': text_height,
                    # Additional attributes such as font, rotation, and color can be specified here.
                    'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                    'rotation': 0,
                    'color': 7
                }
            )
        if (top_bar == 32 and main_bar != 32):
            bot_length =  round(cut_length_top * no_of_bars_top, 3)
            dia_string = str(round(bot_length,3))
            insert_point = (
                15.1 * cell_width,
                start_y - cell_height * 6.9)  # X, Y coordinates where the text will be inserted.
            text_height = 1
            # Add text to the modelspace.
            msp.add_text(
                dia_string,
                dxfattribs={
                    'insert': insert_point,
                    'height': text_height,
                    # Additional attributes such as font, rotation, and color can be specified here.
                    'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                    'rotation': 0,
                    'color': 7
                }
            )
            bot_length = round(cut_length_top * no_of_bars_top, 3)
            dia_string = str(round(bot_length*6.321,3))
            insert_point = (
                15.1 * cell_width,
                start_y - cell_height * 6.9)  # X, Y coordinates where the text will be inserted.
            text_height = 1
            # Add text to the modelspace.
            msp.add_text(
                dia_string,
                dxfattribs={
                    'insert': insert_point,
                    'height': text_height,
                    # Additional attributes such as font, rotation, and color can be specified here.
                    'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                    'rotation': 0,
                    'color': 7
                }
            )
        if (top_bar == 40 and main_bar != 40):
            bot_length = round(cut_length_top * no_of_bars_top, 3)
            dia_string = str(round(bot_length,3))
            insert_point = (
                16.1 * cell_width,
                start_y - cell_height * 6.9)  # X, Y coordinates where the text will be inserted.
            text_height = 1
            # Add text to the modelspace.
            msp.add_text(
                dia_string,
                dxfattribs={
                    'insert': insert_point,
                    'height': text_height,
                    # Additional attributes such as font, rotation, and color can be specified here.
                    'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                    'rotation': 0,
                    'color': 7
                }
            )
            bot_length = round(cut_length_top * no_of_bars_top, 3)
            dia_string = str(round(bot_length*9.877,3))
            insert_point = (
                16.1 * cell_width,
                start_y - cell_height * 8.9)  # X, Y coordinates where the text will be inserted.
            text_height = 1
            # Add text to the modelspace.
            msp.add_text(
                dia_string,
                dxfattribs={
                    'insert': insert_point,
                    'height': text_height,
                    # Additional attributes such as font, rotation, and color can be specified here.
                    'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                    'rotation': 0,
                    'color': 7
                }
            )
        if (top_bar != 12 and main_bar == 12):
            bot_length =  round(cut_length_bottom * no_bars_bottom, 3)
            dia_string = str(bot_length)
            insert_point = (
                11.1 * cell_width,
                start_y - cell_height * 6.9)  # X, Y coordinates where the text will be inserted.
            text_height = 1
            # Add text to the modelspace.
            msp.add_text(
                dia_string,
                dxfattribs={
                    'insert': insert_point,
                    'height': text_height,
                    # Additional attributes such as font, rotation, and color can be specified here.
                    'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                    'rotation': 0,
                    'color': 7
                }
            )
            bot_length = round(cut_length_bottom * no_bars_bottom, 3)
            dia_string = str(round(bot_length*.889,3))
            insert_point = (
                11.1 * cell_width,
                start_y - cell_height * 8.9)  # X, Y coordinates where the text will be inserted.
            text_height = 1
            # Add text to the modelspace.
            msp.add_text(
                dia_string,
                dxfattribs={
                    'insert': insert_point,
                    'height': text_height,
                    # Additional attributes such as font, rotation, and color can be specified here.
                    'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                    'rotation': 0,
                    'color': 7
                }
            )
        if (top_bar != 16 and main_bar == 16):
            bot_length = round(cut_length_bottom * no_bars_bottom, 3)
            dia_string = str(bot_length)
            insert_point = (
                12.1 * cell_width,
                start_y - cell_height * 6.9)  # X, Y coordinates where the text will be inserted.
            text_height = 1
            # Add text to the modelspace.
            msp.add_text(
                dia_string,
                dxfattribs={
                    'insert': insert_point,
                    'height': text_height,
                    # Additional attributes such as font, rotation, and color can be specified here.
                    'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                    'rotation': 0,
                    'color': 7
                }
            )
            bot_length = round(cut_length_bottom * no_bars_bottom, 3)
            dia_string = str(round(bot_length*1.58,3))
            insert_point = (
                12.1 * cell_width,
                start_y - cell_height * 8.9)  # X, Y coordinates where the text will be inserted.
            text_height = 1
            # Add text to the modelspace.
            msp.add_text(
                dia_string,
                dxfattribs={
                    'insert': insert_point,
                    'height': text_height,
                    # Additional attributes such as font, rotation, and color can be specified here.
                    'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                    'rotation': 0,
                    'color': 7
                }
            )
        if (top_bar != 20 and main_bar == 20):
            bot_length = round(cut_length_bottom * no_bars_bottom, 3)
            dia_string = str(bot_length)
            insert_point = (
                13.1 * cell_width,
                start_y - cell_height * 6.9)  # X, Y coordinates where the text will be inserted.
            text_height = 1
            # Add text to the modelspace.
            msp.add_text(
                dia_string,
                dxfattribs={
                    'insert': insert_point,
                    'height': text_height,
                    # Additional attributes such as font, rotation, and color can be specified here.
                    'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                    'rotation': 0,
                    'color': 7
                }
            )
            bot_length = round(cut_length_bottom * no_bars_bottom, 3)
            dia_string = str(round(bot_length*2.469,3))
            insert_point = (
                13.1 * cell_width,
                start_y - cell_height * 8.9)  # X, Y coordinates where the text will be inserted.
            text_height = 1
            # Add text to the modelspace.
            msp.add_text(
                dia_string,
                dxfattribs={
                    'insert': insert_point,
                    'height': text_height,
                    # Additional attributes such as font, rotation, and color can be specified here.
                    'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                    'rotation': 0,
                    'color': 7
                }
            )
        if (top_bar != 25 and main_bar == 25):
            bot_length =  round(cut_length_bottom * no_bars_bottom, 3)
            dia_string = str(bot_length)
            insert_point = (
                14.1 * cell_width,
                start_y - cell_height * 6.9)  # X, Y coordinates where the text will be inserted.
            text_height = 1
            # Add text to the modelspace.
            msp.add_text(
                dia_string,
                dxfattribs={
                    'insert': insert_point,
                    'height': text_height,
                    # Additional attributes such as font, rotation, and color can be specified here.
                    'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                    'rotation': 0,
                    'color': 7
                }
            )
            bot_length = round(cut_length_bottom * no_bars_bottom, 3)
            dia_string = str(round(bot_length*3.858,3))
            insert_point = (
                14.1 * cell_width,
                start_y - cell_height * 8.9)  # X, Y coordinates where the text will be inserted.
            text_height = 1
            # Add text to the modelspace.
            msp.add_text(
                dia_string,
                dxfattribs={
                    'insert': insert_point,
                    'height': text_height,
                    # Additional attributes such as font, rotation, and color can be specified here.
                    'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                    'rotation': 0,
                    'color': 7
                }
            )
        if (top_bar != 32 and main_bar == 32):
            bot_length = round(cut_length_bottom * no_bars_bottom, 3)
            dia_string = str(bot_length)
            insert_point = (
                15.1 * cell_width,
                start_y - cell_height * 6.9)  # X, Y coordinates where the text will be inserted.
            text_height = 1
            # Add text to the modelspace.
            msp.add_text(
                dia_string,
                dxfattribs={
                    'insert': insert_point,
                    'height': text_height,
                    # Additional attributes such as font, rotation, and color can be specified here.
                    'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                    'rotation': 0,
                    'color': 7
                }
            )
            bot_length = round(cut_length_bottom * no_bars_bottom, 3)
            dia_string = str(round(bot_length*6.321,3))
            insert_point = (
                15.1 * cell_width,
                start_y - cell_height * 8.9)  # X, Y coordinates where the text will be inserted.
            text_height = 1
            # Add text to the modelspace.
            msp.add_text(
                dia_string,
                dxfattribs={
                    'insert': insert_point,
                    'height': text_height,
                    # Additional attributes such as font, rotation, and color can be specified here.
                    'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                    'rotation': 0,
                    'color': 7
                }
            )
        if (top_bar != 40 and main_bar == 40):
            bot_length = round(cut_length_bottom * no_bars_bottom, 3)
            dia_string = str(bot_length)
            insert_point = (
                16.1 * cell_width,
                start_y - cell_height * 6.9)  # X, Y coordinates where the text will be inserted.
            text_height = 1
            # Add text to the modelspace.
            msp.add_text(
                dia_string,
                dxfattribs={
                    'insert': insert_point,
                    'height': text_height,
                    # Additional attributes such as font, rotation, and color can be specified here.
                    'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                    'rotation': 0,
                    'color': 7
                }
            )
            bot_length = round(cut_length_bottom * no_bars_bottom, 3)
            dia_string = str(round(bot_length*9.877,3))
            insert_point = (
                16.1 * cell_width,
                start_y - cell_height * 8.9)  # X, Y coordinates where the text will be inserted.
            text_height = 1
            # Add text to the modelspace.
            msp.add_text(
                dia_string,
                dxfattribs={
                    'insert': insert_point,
                    'height': text_height,
                    # Additional attributes such as font, rotation, and color can be specified here.
                    'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                    'rotation': 0,
                    'color': 7
                }
            )


        msp.add_line((6 * cell_width, start_y - 6 * cell_height), (17 * cell_width, start_y - 6 * cell_height))

        #weigth calculation end-----------------------------------------------------------------
        bot_string = "length of Bar (m)"
        insert_point = (
            14* cell_width + .8, start_y +cell_height/2)  # X, Y coordinates where the text will be inserted.
        text_height = 1
        # Add text to the modelspace.
        msp.add_text(
            bot_string,
            dxfattribs={
                'insert': insert_point,
                'height': text_height,
                # Additional attributes such as font, rotation, and color can be specified here.
                'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                'rotation': 0,
                'color': 7
            }
        )
        dia_string = round(10 * 10 / 162, 3)
        insert_point = (
            10.1 * cell_width,
            start_y - cell_height * 7.9)  # X, Y coordinates where the text will be inserted.
        text_height = 1
        # Add text to the modelspace.
        msp.add_text(
            dia_string,
            dxfattribs={
                'insert': insert_point,
                'height': text_height,
                # Additional attributes such as font, rotation, and color can be specified here.
                'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                'rotation': 0,
                'color': 7
            }
        )
        dia_string = round(12 * 12 / 162, 3)
        insert_point = (
            11.1 * cell_width,
            start_y - cell_height * 7.9)  # X, Y coordinates where the text will be inserted.
        text_height = 1
        # Add text to the modelspace.
        msp.add_text(
            dia_string,
            dxfattribs={
                'insert': insert_point,
                'height': text_height,
                # Additional attributes such as font, rotation, and color can be specified here.
                'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                'rotation': 0,
                'color': 7
            }
        )
        dia_string = round(16 * 16 / 162, 3)
        insert_point = (
            12.1 * cell_width,
            start_y - cell_height * 7.9)  # X, Y coordinates where the text will be inserted.
        text_height = 1
        # Add text to the modelspace.
        msp.add_text(
            dia_string,
            dxfattribs={
                'insert': insert_point,
                'height': text_height,
                # Additional attributes such as font, rotation, and color can be specified here.
                'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                'rotation': 0,
                'color': 7
            }
        )
        dia_string = round(20 * 20 / 162, 3)
        insert_point = (
            13.1 * cell_width,
            start_y - cell_height * 7.9)  # X, Y coordinates where the text will be inserted.
        text_height = 1
        # Add text to the modelspace.
        msp.add_text(
            dia_string,
            dxfattribs={
                'insert': insert_point,
                'height': text_height,
                # Additional attributes such as font, rotation, and color can be specified here.
                'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                'rotation': 0,
                'color': 7
            }
        )
        dia_string = round(25 * 25 / 162, 3)
        insert_point = (
            14.1 * cell_width,
            start_y - cell_height * 7.9)  # X, Y coordinates where the text will be inserted.
        text_height = 1
        # Add text to the modelspace.
        msp.add_text(
            dia_string,
            dxfattribs={
                'insert': insert_point,
                'height': text_height,
                # Additional attributes such as font, rotation, and color can be specified here.
                'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                'rotation': 0,
                'color': 7
            }
        )
        dia_string = round(32 * 32 / 162, 3 )
        insert_point = (
            15.1 * cell_width,
            start_y - cell_height * 7.9)  # X, Y coordinates where the text will be inserted.
        text_height = 1
        # Add text to the modelspace.
        msp.add_text(
            dia_string,
            dxfattribs={
                'insert': insert_point,
                'height': text_height,
                # Additional attributes such as font, rotation, and color can be specified here.
                'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                'rotation': 0,
                'color': 7
            }
        )
        dia_string = round(40*40 / 162, 3 )
        insert_point = (
            16.1 * cell_width,
            start_y - cell_height * 7.9)  # X, Y coordinates where the text will be inserted.
        text_height = 1
        # Add text to the modelspace.
        msp.add_text(
            dia_string,
            dxfattribs={
                'insert': insert_point,
                'height': text_height,
                # Additional attributes such as font, rotation, and color can be specified here.
                'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                'rotation': 0,
                'color': 7
            }
        )
        if(stdia==8):
            st_length=round(stirrup_cut_length*no_str,3)
            dia_string = str(st_length)
            insert_point = (
                9.1 * cell_width ,
                start_y - cell_height * 4.9)  # X, Y coordinates where the text will be inserted.
            text_height = 1
            # Add text to the modelspace.
            msp.add_text(
                dia_string,
                dxfattribs={
                    'insert': insert_point,
                    'height': text_height,
                    # Additional attributes such as font, rotation, and color can be specified here.
                    'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                    'rotation': 0,
                    'color': 7
                }
            )
            dia_string = round(8*8/162,3)
            insert_point = (
                9.1 * cell_width ,
                start_y - cell_height *7.9)  # X, Y coordinates where the text will be inserted.
            text_height = 1
            # Add text to the modelspace.
            msp.add_text(
                dia_string,
                dxfattribs={
                    'insert': insert_point,
                    'height': text_height,
                    # Additional attributes such as font, rotation, and color can be specified here.
                    'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                    'rotation': 0,
                    'color': 7
                }
            )
            dia_string = round(8 * 8 / 162 * st_length, 3)
            insert_point = (
                9.1 * cell_width,
                start_y - cell_height * 8.9)  # X, Y coordinates where the text will be inserted.
            text_height = 1
            # Add text to the modelspace.
            msp.add_text(
                dia_string,
                dxfattribs={
                    'insert': insert_point,
                    'height': text_height,
                    # Additional attributes such as font, rotation, and color can be specified here.
                    'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                    'rotation': 0,
                    'color': 7
                }
            )
        if(main_bar==12):
            bot_length = round(cut_length_bottom*no_bars_bottom,3)
            dia_string = str(bot_length)
            insert_point = (
                11 * cell_width + .8,
                start_y - cell_height * 4 + .5)  # X, Y coordinates where the text will be inserted.
            text_height = 1
            # Add text to the modelspace.
            msp.add_text(
                dia_string,
                dxfattribs={
                    'insert': insert_point,
                    'height': text_height,
                    # Additional attributes such as font, rotation, and color can be specified here.
                    'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                    'rotation': 0,
                    'color': 7
                }
            )

        elif (main_bar == 16):
            bot_length = round(cut_length_bottom*no_bars_bottom,3)
            dia_string = str(bot_length)
            insert_point = (
                12.1 * cell_width ,
                start_y - cell_height * 3.9)  # X, Y coordinates where the text will be inserted.
            text_height = 1
            # Add text to the modelspace.
            msp.add_text(
                dia_string,
                dxfattribs={
                    'insert': insert_point,
                    'height': text_height,
                    # Additional attributes such as font, rotation, and color can be specified here.
                    'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                    'rotation': 0,
                    'color': 7
                }
            )

        elif (main_bar == 20):
            bot_length = round(cut_length_bottom*no_bars_bottom,3)
            dia_string = str(bot_length)
            insert_point = (
                13.1 * cell_width ,
                start_y - cell_height * 3.9)  # X, Y coordinates where the text will be inserted.
            text_height = 1
            # Add text to the modelspace.
            msp.add_text(
                dia_string,
                dxfattribs={
                    'insert': insert_point,
                    'height': text_height,
                    # Additional attributes such as font, rotation, and color can be specified here.
                    'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                    'rotation': 0,
                    'color': 7
                }
            )

        elif (main_bar == 25):
            bot_length = round(cut_length_bottom*no_bars_bottom,3)
            dia_string = str(bot_length)
            insert_point = (
                14.1 * cell_width ,
                start_y - cell_height * 3.9)  # X, Y coordinates where the text will be inserted.
            text_height = 1
            # Add text to the modelspace.
            msp.add_text(
                dia_string,
                dxfattribs={
                    'insert': insert_point,
                    'height': text_height,
                    # Additional attributes such as font, rotation, and color can be specified here.
                    'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                    'rotation': 0,
                    'color': 7
                }
            )

        elif (main_bar == 32):
            bot_length = round(cut_length_bottom*no_bars_bottom,3)
            dia_string = str(bot_length)
            insert_point = (
                15.1 * cell_width,
                start_y - cell_height * 3.9)  # X, Y coordinates where the text will be inserted.
            text_height = 1
            # Add text to the modelspace.
            msp.add_text(
                dia_string,
                dxfattribs={
                    'insert': insert_point,
                    'height': text_height,
                    # Additional attributes such as font, rotation, and color can be specified here.
                    'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                    'rotation': 0,
                    'color': 7
                }
            )

        elif (main_bar == 40):
            bot_length =round(cut_length_bottom*no_bars_bottom,3)
            dia_string = str(bot_length)
            insert_point = (
                16.1 * cell_width ,
                start_y - cell_height * 3.9)  # X, Y coordinates where the text will be inserted.
            text_height = 1
            # Add text to the modelspace.
            msp.add_text(
                dia_string,
                dxfattribs={
                    'insert': insert_point,
                    'height': text_height,
                    # Additional attributes such as font, rotation, and color can be specified here.
                    'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                    'rotation': 0,
                    'color': 7
                }
            )

        #-----------------------------------------------------------------------------top dia total length
        if (top_bar == 12):
            top_length = round(cut_length_top*no_of_bars_top,3)
            dia_string = str(top_length)
            insert_point = (
                11.1 * cell_width ,
                start_y - cell_height * 2.9)  # X, Y coordinates where the text will be inserted.
            text_height = 1
            # Add text to the modelspace.
            msp.add_text(
                dia_string,
                dxfattribs={
                    'insert': insert_point,
                    'height': text_height,
                    # Additional attributes such as font, rotation, and color can be specified here.
                    'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                    'rotation': 0,
                    'color': 7
                }
            )
        elif (top_bar == 16):
            top_length = round(cut_length_top*no_of_bars_top,3)
            dia_string = str(top_length)
            insert_point = (
            12 * cell_width + .8,
            start_y - cell_height * 3 + .5)  # X, Y coordinates where the text will be inserted.
            text_height = 1
        # Add text to the modelspace.
            msp.add_text(
                dia_string,
            dxfattribs={
                'insert': insert_point,
                'height': text_height,
                # Additional attributes such as font, rotation, and color can be specified here.
                'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                'rotation': 0,
                'color': 7
                }
             )

        elif (top_bar == 20):
            top_length = round(cut_length_top*no_of_bars_top,3)
            dia_string = str(top_length)
            insert_point = (13 * cell_width + .8, start_y - cell_height * 3 + .5)  # X, Y coordinates where the text will be inserted.
            text_height = 1
# Add text to the modelspace.
            msp.add_text(
             dia_string,
            dxfattribs={
        'insert': insert_point,
        'height': text_height,
        # Additional attributes such as font, rotation, and color can be specified here.
        'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
        'rotation': 0,
        'color': 7
            }
            )
        elif (top_bar == 25):
            top_length = round(cut_length_top*no_of_bars_top,3)
            dia_string = str(top_length)
            insert_point = (14 * cell_width + .8, start_y - cell_height * 3 + .5)  # X, Y coordinates where the text will be inserted.
            text_height = 1
# Add text to the modelspace.
            msp.add_text(
            dia_string,
            dxfattribs={
        'insert': insert_point,
        'height': text_height,
        # Additional attributes such as font, rotation, and color can be specified here.
        'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
        'rotation': 0,
        'color': 7
        }
        )
        elif (top_bar == 32):
            top_length = round(cut_length_top*no_of_bars_top,3)
            dia_string = str(top_length)
            insert_point = (15 * cell_width + .8,start_y - cell_height * 3 + .5)  # X, Y coordinates where the text will be inserted.
            text_height = 1
# Add text to the modelspace.
            msp.add_text(
                dia_string,
                dxfattribs={
        'insert': insert_point,
        'height': text_height,
        # Additional attributes such as font, rotation, and color can be specified here.
        'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
        'rotation': 0,
        'color': 7
                }
            )
        elif (top_bar == 40):
            top_length = round(cut_length_top*no_of_bars_top,3)
            dia_string = str(top_length)
            insert_point = (16 * cell_width + .8,start_y - cell_height * 3 + .5)  # X, Y coordinates where the text will be inserted.
            text_height = 1
# Add text to the modelspace.
            msp.add_text(
             dia_string,
                dxfattribs={
                'insert': insert_point,
                 'height': text_height,
        # Additional attributes such as font, rotation, and color can be specified here.
                 'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
             'rotation': 0,
                'color': 7
                }
                )
#side face reinforcement -------------------------------------------------------------------------------------------
        if(o_d >= 750):
            msp.add_line((1.3*cell_width,start_y - cell_height * 5.5),(1.8*cell_width,start_y - cell_height * 5.5))
            dia_string = "Side Face "
            insert_point = (
            .1 * cell_width , start_y - cell_height * 5.5)  # X, Y coordinates where the text will be inserted.
            text_height = .5
            # Add text to the modelspace.
            msp.add_text(
                dia_string,
                dxfattribs={
                    'insert': insert_point,
                    'height': text_height,
                    # Additional attributes such as font, rotation, and color can be specified here.
                    'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                    'rotation': 0,
                    'color': 7
                }
            )
            bar_string = "Nil"
            insert_point = (
                4.5 * cell_width, start_y - cell_height * 5.5)  # X, Y coordinates where the text will be inserted.
            text_height = .5
            # Add text to the modelspace.
            msp.add_text(
                bar_string,
                dxfattribs={
                    'insert': insert_point,
                    'height': text_height,
                    # Additional attributes such as font, rotation, and color can be specified here.
                    'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                    'rotation': 0,
                    'color': 7
                }
            )
            bar_string = "Nil"
            insert_point = (
                2.5 * cell_width, start_y - cell_height * 5.5)  # X, Y coordinates where the text will be inserted.
            text_height = .5
            # Add text to the modelspace.
            msp.add_text(
                bar_string,
                dxfattribs={
                    'insert': insert_point,
                    'height': text_height,
                    # Additional attributes such as font, rotation, and color can be specified here.
                    'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                    'rotation': 0,
                    'color': 7
                }
            )
            bar_string = "Nil"
            insert_point = (
                6.5 * cell_width, start_y - cell_height * 5.5)  # X, Y coordinates where the text will be inserted.
            text_height = .5
            # Add text to the modelspace.
            msp.add_text(
                bar_string,
                dxfattribs={
                    'insert': insert_point,
                    'height': text_height,
                    # Additional attributes such as font, rotation, and color can be specified here.
                    'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                    'rotation': 0,
                    'color': 7
                }
            )
            dia_string = "b"
            insert_point = (
                1.45 * cell_width, start_y - cell_height * 5.4)  # X, Y coordinates where the text will be inserted.
            text_height = .5
            # Add text to the modelspace.
            msp.add_text(
                dia_string,
                dxfattribs={
                    'insert': insert_point,
                    'height': text_height,
                    # Additional attributes such as font, rotation, and color can be specified here.
                    'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                    'rotation': 0,
                    'color': 7
                }
            )
            side_length=clear_span*100000-200*nominal_cover+wall_thickness*200
            dia_string = str(side_length/1000)
            insert_point = (
                3.45 * cell_width, start_y - cell_height * 5.4)  # X, Y coordinates where the text will be inserted.
            text_height = .5
            # Add text to the modelspace.
            msp.add_text(
                dia_string,
                dxfattribs={
                    'insert': insert_point,
                    'height': text_height,
                    # Additional attributes such as font, rotation, and color can be specified here.
                    'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                    'rotation': 0,
                    'color': 7
                }
            )
            dia_string = str(no_of_bars_side*2)
            insert_point = (
                8.1 * cell_width, start_y - cell_height * 5.9)  # X, Y coordinates where the text will be inserted.
            text_height = .8
            # Add text to the modelspace.
            msp.add_text(
                dia_string,
                dxfattribs={
                    'insert': insert_point,
                    'height': text_height,
                    # Additional attributes such as font, rotation, and color can be specified here.
                    'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                    'rotation': 0,
                    'color': 7
                }
            )
            dia_string = str(side_length/1000)
            insert_point = (
                7.1 * cell_width, start_y - cell_height * 5.9)  # X, Y coordinates where the text will be inserted.
            text_height = .8
            # Add text to the modelspace.
            msp.add_text(
                dia_string,
                dxfattribs={
                    'insert': insert_point,
                    'height': text_height,
                    # Additional attributes such as font, rotation, and color can be specified here.
                    'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                    'rotation': 0,
                    'color': 7
                }
            )
            dia_string = str(side_bar)
            insert_point = (
                5.5 * cell_width, start_y - cell_height * 5.9)  # X, Y coordinates where the text will be inserted.
            text_height = .8
            # Add text to the modelspace.
            msp.add_text(
                dia_string,
                dxfattribs={
                    'insert': insert_point,
                    'height': text_height,
                    # Additional attributes such as font, rotation, and color can be specified here.
                    'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                    'rotation': 0,
                    'color': 7
                }
            )
            dia_string = " Side Face Weight Reinforcement  is Directly Added at the end to avoid confusion"
            insert_point = (
                17.1 * cell_width, start_y - cell_height * 8.9)  # X, Y coordinates where the text will be inserted.
            text_height = 1
            # Add text to the modelspace.
            msp.add_text(
                dia_string,
                dxfattribs={
                    'insert': insert_point,
                    'height': text_height,
                    # Additional attributes such as font, rotation, and color can be specified here.
                    'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                    'rotation': 0,
                    'color': 7
                }
            )
            if(side_bar==12):
                dia_string = str(side_length*no_of_bars_side*2/1000)
                insert_point = (
                    11.1 * cell_width, start_y - cell_height * 5.9)  # X, Y coordinates where the text will be inserted.
                text_height = .8
                # Add text to the modelspace.
                msp.add_text(
                    dia_string,
                    dxfattribs={
                        'insert': insert_point,
                        'height': text_height,
                        # Additional attributes such as font, rotation, and color can be specified here.
                        'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                        'rotation': 0,
                        'color': 7
                    }
                )

            if (side_bar == 16):
                dia_string = str(side_length * no_of_bars_side * 2 / 1000)
                insert_point = (
                    12.1 * cell_width, start_y - cell_height * 5.9)  # X, Y coordinates where the text will be inserted.
                text_height = .8
                # Add text to the modelspace.
                msp.add_text(
                    dia_string,
                    dxfattribs={
                        'insert': insert_point,
                        'height': text_height,
                        # Additional attributes such as font, rotation, and color can be specified here.
                        'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                        'rotation': 0,
                        'color': 7
                    }
                )

            if (side_bar == 20):
                dia_string = str(side_length * no_of_bars_side * 2 / 1000)
                insert_point = (
                    13.1 * cell_width, start_y - cell_height * 5.9)  # X, Y coordinates where the text will be inserted.
                text_height = .8
                # Add text to the modelspace.
                msp.add_text(
                    dia_string,
                    dxfattribs={
                        'insert': insert_point,
                        'height': text_height,
                        # Additional attributes such as font, rotation, and color can be specified here.
                        'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                        'rotation': 0,
                        'color': 7
                    }
                )
            if (side_bar == 25):
                dia_string = str(side_length * no_of_bars_side * 2 / 1000)
                insert_point = (
                    14.1 * cell_width, start_y - cell_height * 5.9)  # X, Y coordinates where the text will be inserted.
                text_height = .8
                # Add text to the modelspace.
                msp.add_text(
                    dia_string,
                    dxfattribs={
                        'insert': insert_point,
                        'height': text_height,
                        # Additional attributes such as font, rotation, and color can be specified here.
                        'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                        'rotation': 0,
                        'color': 7
                    }
                )
            if (side_bar == 32):
                dia_string = str(side_length * no_of_bars_side * 2 / 1000)
                insert_point = (
                    15.1 * cell_width, start_y - cell_height * 5.9)  # X, Y coordinates where the text will be inserted.
                text_height = .8
                # Add text to the modelspace.
                msp.add_text(
                    dia_string,
                    dxfattribs={
                        'insert': insert_point,
                        'height': text_height,
                        # Additional attributes such as font, rotation, and color can be specified here.
                        'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                        'rotation': 0,
                        'color': 7
                    }
                )
            if (side_bar == 40):
                dia_string = str(side_length * no_of_bars_side * 2 / 1000)
                insert_point = (
                    16.1 * cell_width, start_y - cell_height * 5.9)  # X, Y coordinates where the text will be inserted.
                text_height = .8
                # Add text to the modelspace.
                msp.add_text(
                    dia_string,
                    dxfattribs={
                        'insert': insert_point,
                        'height': text_height,
                        # Additional attributes such as font, rotation, and color can be specified here.
                        'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                        'rotation': 0,
                        'color': 7
                    }
                )
        if (o_d >= 750):
            if(side_bar==12):
                side_l = round(side_length * no_of_bars_side * .889 *2/ 1000, 3)
            elif (side_bar == 16):
                side_l = round(side_length * no_of_bars_side * 1.58 * 2 / 1000, 3)
            elif (side_bar == 20):
                side_l = round(side_length * no_of_bars_side * 2.469 * 2 / 1000, 3)
            elif (side_bar == 25):
                side_l = round(side_length * no_of_bars_side * 3.858 * 2 / 1000, 3)
            elif (side_bar == 32):
                side_l = round(side_length * no_of_bars_side * 6.321 * 2 / 1000, 3)
            elif (side_bar == 40):
                side_l = round(side_length * no_of_bars_side * 9.887 * 2 / 1000, 3)
        else:
            side_l = 0
        bot_length = round(cut_length_bottom * no_bars_bottom * main_bar * main_bar / 162, 3) + round(
            cut_length_top * no_of_bars_top * top_bar * top_bar / 162, 3) + round(
            stirrup_cut_length * no_str * stdia * stdia / 162, 3) + side_l
        dia_string = str(round(bot_length, 3))
        insert_point = (
            13.1 * cell_width,
            start_y - cell_height * 9.9)  # X, Y coordinates where the text will be inserted.
        text_height = 1
        # Add text to the modelspace.
        msp.add_text(
            dia_string,
            dxfattribs={
                'insert': insert_point,
                'height': text_height,
                # Additional attributes such as font, rotation, and color can be specified here.
                'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                'rotation': 0,
                'color': 7
            }
        )



        # cuuting m
        dia_string="(m)"
        insert_point = (
            7.5 * cell_width,
            start_y - cell_height * 1.5)  # X, Y coordinates where the text will be inserted.
        text_height = .5
        # Add text to the modelspace.
        msp.add_text(
            dia_string,
            dxfattribs={
                'insert': insert_point,
                'height': text_height,
                # Additional attributes such as font, rotation, and color can be specified here.
                'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                'rotation': 0,
                'color': 7
            }
        )
        dia_string = "No's"
        insert_point = (
            8.5 * cell_width,
            start_y - cell_height * 1.5)  # X, Y coordinates where the text will be inserted.
        text_height = .5
        # Add text to the modelspace.
        msp.add_text(
            dia_string,
            dxfattribs={
                'insert': insert_point,
                'height': text_height,
                # Additional attributes such as font, rotation, and color can be specified here.
                'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                'rotation': 0,
                'color': 7
            }
        )
#dia total length end------------------------------------------------------------------------------------------
        headers = [
            "Type", "Bar Shape", "a (m)", "b (m)", "c (m)",
            "Dia (mm)", "Spacing (mm)", "Cutting Length ", "  ","8 (mm)", "10 (mm)", "12 (mm)", "16 (mm)", "20 (mm)", "25 (mm)", "32 (mm)","40 (mm)"
        ]


        # Number of rows
        num_rows = 4
        total_columns = len(headers)

        # Create headers
        for i, header in enumerate(headers):
            x = start_x + i * cell_width
            msp.add_lwpolyline(
                [(x, start_y), (x + cell_width, start_y), (x + cell_width, start_y - header_height),
                 (x, start_y - header_height), (x, start_y)],
                close=True
            )

            msp.add_text(header, dxfattribs={'height': .5}).set_dxf_attrib('insert',
                                                                               (x + .5, start_y - header_height / 2))

        # Add length headers



        # Creating Rows
        for row in range(num_rows):
            for col in range(total_columns):
                x = start_x + col * cell_width
                y = start_y - header_height - (row + 1) * cell_height

                # Draw the cell
                msp.add_lwpolyline(
                    [(x, y), (x + cell_width, y), (x + cell_width, y + cell_height), (x, y + cell_height), (x, y)],
                    close=True
                )

                # Sample text filling (you can fill in actual data)
                if col == 0:
                    text = str(row + 1)  # Bar no.
                elif col == 1 and row == 0:  # First row, Bar Shape
                    # Example shape: U-shaped bar
                    shape_x = x + cell_width / 2
                    shape_y = y + cell_height / 2
                    msp.add_lwpolyline([(shape_x - 2, shape_y), (shape_x + 2, shape_y)],
                                       dxfattribs={'layer': '0'})  # Horizontal line
                    msp.add_lwpolyline([(shape_x - 2, shape_y), (shape_x - 2, shape_y + 1)],
                                       dxfattribs={'layer': '0'})  # Vertical line left
                    msp.add_lwpolyline([(shape_x + 2, shape_y), (shape_x + 2, shape_y + 1)],
                                       dxfattribs={'layer': '0'})  # Vertical line right
                    continue
                elif col < len(headers):  # Dummy text for other cells
                    text = f'R{row + 1}C{col + 1}'
                else:  # Dummy length values
                    text = str(round((row + 1) * (col + 1) / 10, 2))




        #--------------------------------------------------END BBS---------------------------------------------------------------
        xe = -wall_thickness + nominal_cover + wall_thickness / 2
        ye = overall_depth - nominal_cover * 2
        x1e = clear_span * 200 + 50 * top_bar_provided / 100
        y1e = overall_depth - nominal_cover * 2
        x3e = clear_span * 1000 + wall_thickness - nominal_cover - wall_thickness / 2
        y3e = o_d / 100 - nominal_cover * 2
        x4e = clear_span * 800 - 50 * top_bar_provided / 100
        y4e = o_d / 100 - nominal_cover * 2
        dim3 = msp.add_linear_dim(
            base=(150 * clear_span, 1.1 * overall_depth),  # location of the dimension line
            p1=(0, overall_depth - nominal_cover / 100),  # 1st measurement point
            p2=(x1e, overall_depth - nominal_cover / 100),  # 2nd measurement point
            dimstyle="EZDXF",  # default dimension style
        )
        dim3 = msp.add_linear_dim(
            base=(500 * clear_span, 1.1 * overall_depth),  # location of the dimension line
            p1=(x4e, overall_depth - nominal_cover / 100),  # 1st measurement point
            p2=(x1e, overall_depth - nominal_cover / 100),  # 2nd measurement point
            dimstyle="EZDXF",  # default dimension style
        )
        dim3 = msp.add_linear_dim(
            base=(750 * clear_span, 1.1 * overall_depth),  # location of the dimension line
            p1=(x4e, overall_depth - nominal_cover / 100),  # 1st measurement point
            p2=(x3e - wall_thickness / 2 + nominal_cover, overall_depth - nominal_cover / 100),  # 2nd measurement point
            dimstyle="EZDXF",  # default dimension style
        )

        # Create a Line
        msp.add_line((xe, o_d / 100 - nominal_cover * 2), (x1e, o_d / 100 - nominal_cover * 2))  # top bar
        msp.add_line((x1e, o_d / 100 - nominal_cover * 2), (x1e + nominal_cover, o_d / 100 - nominal_cover * 4))
        msp.add_line((x3e, y3e), (x4e, y4e))  # top left
        msp.add_line((x4e - nominal_cover, o_d / 100 - nominal_cover * 4), (x4e, y4e))
        msp.add_line((x1e, 2 * nominal_cover), (x4e, 2 * nominal_cover))  # bottom extra
        msp.add_line((x1e, 2 * nominal_cover),
                     (x1e - nominal_cover, 4 * nominal_cover))  # bottom extra
        msp.add_line((x4e, 2 * nominal_cover),
                     (x4e + nominal_cover, 4 * nominal_cover))
        #detailing text----------------------------------------------------------------------------
        text_string = f"6. Top Reinforcemnet :- Provide {no_of_bars_top} no's of {top_bar} mm throughout the top and {no_of_bars_bottom//2} no's of {main_bar} mm curtail at L/3 from the face of the support"
        insert_point = (20 + 1000 * clear_span, 1)  # X, Y coordinates where the text will be inserted.
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
        text_string = f"5. Bottom Reinforcemnet :- Provide {no_of_bars_top} no's of {main_bar} mm throughout the Bottom and {no_of_bars_bottom//2} no's of {main_bar} mm curtail at L/3 from the face of the support"
        insert_point = (20 + 1000 * clear_span, 3)  # X, Y coordinates where the text will be inserted.
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
        text_string = f"4. Shear Reinforcemnet :- Provide {stdia} mm as vertical stirrups @ {max_spacing} mm c/c "
        insert_point = (20 + 1000 * clear_span, 5)  # X, Y coordinates where the text will be inserted.
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
        ml = round(ml, 3)
        mu = round(mu, 3)
        sf = round(ultimate_shear_force, 3)
        text_string = f"3. Mulimt :- {ml} KNm , Ultimate Bending Moment :- {mu} kNm ,Ultimate Shear Force :- {sf} kN"
        insert_point = (20 + 1000 * clear_span, 7)  # X, Y coordinates where the text will be inserted.
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
        text_string = f"2. Concrete Grade :- {fck} MPa , Steel Grade :- fe{fy}  "
        insert_point = (20 + 1000 * clear_span, 9)  # X, Y coordinates where the text will be inserted.
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
        text_string = f"1. Nominal Cover :- {nominal_cover * 100} mm  "
        insert_point = (20 + 1000 * clear_span, 11)  # X, Y coordinates where the text will be inserted.
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
        text_string = f"Notes :- "
        insert_point = (10 + 1000 * clear_span, 15)  # X, Y coordinates where the text will be inserted.
        text_height = 2  # Height of the text.

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
        text_string = f"7. Ductlie Reinforcement is Provided with minimum consideration"
        insert_point = (20 + 1000 * clear_span, -1)  # X, Y coordinates where the text will be inserted.
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
        start_point = (10 + 1000 * clear_span, 13)
        end_point = (140 + 1000 * clear_span, 13)

        msp.add_line(start_point, end_point, dxfattribs={
            'color': 7,  # Optional: specify the color
            'linetype': 'DASHED'  # Apply the hidden linetype
        })
        start_point = (10 + 1000 * clear_span, 13)
        end_point = (10 + 1000 * clear_span, -3)

        msp.add_line(start_point, end_point, dxfattribs={
            'color': 7,  # Optional: specify the color
            'linetype': 'DASHED'  # Apply the hidden linetype
        })
        start_point = (140 + 1000 * clear_span, 13)
        end_point = (140 + 1000 * clear_span, -3)

        msp.add_line(start_point, end_point, dxfattribs={
            'color': 7,  # Optional: specify the color
            'linetype': 'DASHED'  # Apply the hidden linetype
        })
        start_point = (10 + 1000 * clear_span, -3)
        end_point = (140 + 1000 * clear_span, -3)

        msp.add_line(start_point, end_point, dxfattribs={
            'color': 7,  # Optional: specify the color
            'linetype': 'DASHED'  # Apply the hidden linetype
        })
        # ast details
        ast = max(ast, astmin)
        a = round(ast, 3)
        txt_content = f"Ast Required in Tension Region  :- {a} mm2"
        insert_point = (
            20 + 1000 * clear_span, 40)  # X, Y coordinates where the text will be inserted.
        text_height = .8
        # Add text to the modelspace.
        msp.add_text(
            txt_content,
            dxfattribs={
                'insert': insert_point,
                'height': text_height,
                # Additional attributes such as font, rotation, and color can be specified here.
                'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                'rotation': 0,
                'color': 7
            }
        )
        txt_content = f"Dia of Bar             No's         Ast Provided mm2                 Pt(%)"
        insert_point = (
            20 + 1000 * clear_span, 38)  # X, Y coordinates where the text will be inserted.
        text_height = .8
        # Add text to the modelspace.
        msp.add_text(
            txt_content,
            dxfattribs={
                'insert': insert_point,
                'height': text_height,
                # Additional attributes such as font, rotation, and color can be specified here.
                'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                'rotation': 0,
                'color': 7
            }
        )

        x12 = math.ceil(ast / 113.041)
        a12 = round(x12 * 113.041, 3)
        p12 = round(100 * a12 / (b * effective_depth), 3)
        txt_content = f"12 mm                {x12}               {a12}                     {p12}"
        insert_point = (
            20 + 1000 * clear_span, 36)  # X, Y coordinates where the text will be inserted.
        text_height = .8
        # Add text to the modelspace.
        msp.add_text(
            txt_content,
            dxfattribs={
                'insert': insert_point,
                'height': text_height,
                # Additional attributes such as font, rotation, and color can be specified here.
                'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                'rotation': 0,
                'color': 7
            }
        )
        x12 = math.ceil(ast / 200.961)
        a12 = round(x12 * 200.961, 3)
        p12 = round(100 * a12 / (b * effective_depth), 3)
        txt_content = f"16 mm                {x12}               {a12}                     {p12}"
        insert_point = (
            20 + 1000 * clear_span, 34)  # X, Y coordinates where the text will be inserted.
        text_height = .8
        # Add text to the modelspace.
        msp.add_text(
            txt_content,
            dxfattribs={
                'insert': insert_point,
                'height': text_height,
                # Additional attributes such as font, rotation, and color can be specified here.
                'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                'rotation': 0,
                'color': 7
            }
        )
        x12 = math.ceil(ast / 314.001)
        a12 = round(x12 * 314.001, 3)
        p12 = round(100 * a12 / (b * effective_depth), 3)
        txt_content = f"20 mm                {x12}               {a12}                     {p12}"
        insert_point = (
            20 + 1000 * clear_span, 32)  # X, Y coordinates where the text will be inserted.
        text_height = .8
        # Add text to the modelspace.
        msp.add_text(
            txt_content,
            dxfattribs={
                'insert': insert_point,
                'height': text_height,
                # Additional attributes such as font, rotation, and color can be specified here.
                'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                'rotation': 0,
                'color': 7
            }
        )
        x12 = math.ceil(ast / 490.625)
        a12 = round(x12 * 490.625, 3)
        p12 = round(100 * a12 / (b * effective_depth), 3)
        txt_content = f"25 mm                {x12}               {a12}                     {p12}"
        insert_point = (
            20 + 1000 * clear_span, 30)  # X, Y coordinates where the text will be inserted.
        text_height = .8
        # Add text to the modelspace.
        msp.add_text(
            txt_content,
            dxfattribs={
                'insert': insert_point,
                'height': text_height,
                # Additional attributes such as font, rotation, and color can be specified here.
                'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                'rotation': 0,
                'color': 7
            }
        )
        x12 = math.ceil(ast / 803.841)
        a12 = round(x12 * 803.841, 3)
        p12 = round(100 * a12 / (b * effective_depth), 3)
        txt_content = f"32 mm                {x12}               {a12}                     {p12}"
        insert_point = (
            20 + 1000 * clear_span, 28)  # X, Y coordinates where the text will be inserted.
        text_height = .8
        # Add text to the modelspace.
        msp.add_text(
            txt_content,
            dxfattribs={
                'insert': insert_point,
                'height': text_height,
                # Additional attributes such as font, rotation, and color can be specified here.
                'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                'rotation': 0,
                'color': 7
            }
        )
        x12 = math.ceil(ast / 1256.001)
        a12 = round(x12 * 1256.001, 3)
        p12 = round(100 * a12 / (b * effective_depth), 3)
        txt_content = f"40 mm                {x12}               {a12}                     {p12}"
        insert_point = (
            20 + 1000 * clear_span, 26)  # X, Y coordinates where the text will be inserted.
        text_height = .8
        # Add text to the modelspace.
        msp.add_text(
            txt_content,
            dxfattribs={
                'insert': insert_point,
                'height': text_height,
                # Additional attributes such as font, rotation, and color can be specified here.
                'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                'rotation': 0,
                'color': 7
            }
        )
        # ast details---------------------
        ast=max(ast,astmin)
        a = round(ast, 3)
        txt_content = f"Ast Required in Tension Region :- {a} mm2"
        insert_point = (
            20 + 1000 * clear_span, 40)  # X, Y coordinates where the text will be inserted.
        text_height = .8
        # Add text to the modelspace.
        msp.add_text(
            txt_content,
            dxfattribs={
                'insert': insert_point,
                'height': text_height,
                # Additional attributes such as font, rotation, and color can be specified here.
                'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                'rotation': 0,
                'color': 7
            }
        )
        txt_content = f"Dia of Bar             No's         Ast Provided mm2                 Pt(%)"
        insert_point = (
            20 + 1000 * clear_span, 38)  # X, Y coordinates where the text will be inserted.
        text_height = .8
        # Add text to the modelspace.
        msp.add_text(
            txt_content,
            dxfattribs={
                'insert': insert_point,
                'height': text_height,
                # Additional attributes such as font, rotation, and color can be specified here.
                'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                'rotation': 0,
                'color': 7
            }
        )

        x12 = math.ceil(ast / 113.041)
        a12 = round(x12 * 113.041, 3)
        p12 = round(100 * a12 / (b * effective_depth), 3)
        txt_content = f"12 mm                {x12}               {a12}                     {p12}"
        insert_point = (
            20 + 1000 * clear_span, 36)  # X, Y coordinates where the text will be inserted.
        text_height = .8
        # Add text to the modelspace.
        msp.add_text(
            txt_content,
            dxfattribs={
                'insert': insert_point,
                'height': text_height,
                # Additional attributes such as font, rotation, and color can be specified here.
                'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                'rotation': 0,
                'color': 7
            }
        )
        x12 = math.ceil(ast / 200.961)
        a12 = round(x12 * 200.961, 3)
        p12 = round(100 * a12 / (b * effective_depth), 3)
        txt_content = f"16 mm                {x12}               {a12}                     {p12}"
        insert_point = (
            20 + 1000 * clear_span, 34)  # X, Y coordinates where the text will be inserted.
        text_height = .8
        # Add text to the modelspace.
        msp.add_text(
            txt_content,
            dxfattribs={
                'insert': insert_point,
                'height': text_height,
                # Additional attributes such as font, rotation, and color can be specified here.
                'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                'rotation': 0,
                'color': 7
            }
        )
        x12 = math.ceil(ast / 314.001)
        a12 = round(x12 * 314.001, 3)
        p12 = round(100 * a12 / (b * effective_depth), 3)
        txt_content = f"20 mm                {x12}               {a12}                     {p12}"
        insert_point = (
            20 + 1000 * clear_span, 32)  # X, Y coordinates where the text will be inserted.
        text_height = .8
        # Add text to the modelspace.
        msp.add_text(
            txt_content,
            dxfattribs={
                'insert': insert_point,
                'height': text_height,
                # Additional attributes such as font, rotation, and color can be specified here.
                'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                'rotation': 0,
                'color': 7
            }
        )
        x12 = math.ceil(ast / 490.625)
        a12 = round(x12 * 490.625, 3)
        p12 = round(100 * a12 / (b * effective_depth), 3)
        txt_content = f"25 mm                {x12}               {a12}                     {p12}"
        insert_point = (
            20 + 1000 * clear_span, 30)  # X, Y coordinates where the text will be inserted.
        text_height = .8
        # Add text to the modelspace.
        msp.add_text(
            txt_content,
            dxfattribs={
                'insert': insert_point,
                'height': text_height,
                # Additional attributes such as font, rotation, and color can be specified here.
                'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                'rotation': 0,
                'color': 7
            }
        )
        x12 = math.ceil(ast / 803.841)
        a12 = round(x12 * 803.841, 3)
        p12 = round(100 * a12 / (b * effective_depth), 3)
        txt_content = f"32 mm                {x12}               {a12}                     {p12}"
        insert_point = (
            20 + 1000 * clear_span, 28)  # X, Y coordinates where the text will be inserted.
        text_height = .8
        # Add text to the modelspace.
        msp.add_text(
            txt_content,
            dxfattribs={
                'insert': insert_point,
                'height': text_height,
                # Additional attributes such as font, rotation, and color can be specified here.
                'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                'rotation': 0,
                'color': 7
            }
        )
        x12 = math.ceil(ast / 1256.001)
        a12 = round(x12 * 1256.001, 3)
        p12 = round(100 * a12 / (b * effective_depth), 3)
        txt_content = f"40 mm                {x12}               {a12}                     {p12}"
        insert_point = (
            20 + 1000 * clear_span, 26)  # X, Y coordinates where the text will be inserted.
        text_height = .8
        # Add text to the modelspace.
        msp.add_text(
            txt_content,
            dxfattribs={
                'insert': insert_point,
                'height': text_height,
                # Additional attributes such as font, rotation, and color can be specified here.
                'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                'rotation': 0,
                'color': 7
            }
        )
        print(spant)
        if (pt >= 4):
            return ("Tension Reinforcement Exceeds 4%")
            sys.exit()
        dis_bar = top_bar
        lef = clear_span * 1000 + wall_thickness
        tl = live_load + 25 * b * overall_depth
        span_d = 15
        deff = effective_depth
        astreq = ast
        xorigin = clear_span
        width = clear_span
        ubm = ultimate_bending_moment
        sfm = ultimate_shear_force
        astshorprov = (main_bar * main_bar * 0.7857) * no_of_bars_top
        pst = (100 * astshorprov) / (1000 * effective_depth)
        astshorprov = (dis_bar * dis_bar * 0.7857) * no_of_bars_top
        plt = (100 * astshorprov) / (1000 * effective_depth)
        texts = [
            f"                                   Design of Simply Supported Beam ",
            "Input Data:- - -  - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -",
            f"Effective Length                  ={lef * 100:.2f} mm",
            f"Width of the support              ={wall_thickness * 100} mm",
            f"Grade of Concrete                 ={fck} MPa",
            f"Grade of steel                    =fe{fy} ",
            f"Imposed Load                      ={ll} kN/m",
            f"Self Weight                       ={odt * 25 * wtt / 1000000:.2f} kN/m",
            f"Total Load                        ={ll + odt * 25 * wtt / 1000000:.2f} kN/m",
            "Dimensions:- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -  ",
            f"Span/d ratio                       ={spant:.2f}",
            f"Effective Cover                    ={overall_depth * 100 - effective_depth} mm",
            f"Overall Depth                      ={overall_depth * 100}mm",
            "Analysis of Slab- -  - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - ",
            f"Factor of Safety                   =1.5 ",
            f"Ultimate Bending Moment             ={mu :.2f} kNm/m",
            f"Ultimate shear force               ={sf:.2f} kN/m",
            "Moment of Resistance of the Slab- -  - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -",
            "Short Span :-",
            f"Mux,l                                ={Ml / 10 ** 6:.2f} kNm/m",
            f"Depth of Neutral Axis                ={xumax * deff:.2f} mm",
            "Mux < Mux,l ,The section is singly reinforced ",
            "Area of Steel Tension (Bottom Bars)- -  - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - ",
            f"Ast:-                                  ={astreq:.2f} mm2 ",
            f"Ast,min                                ={astmin:.2f} mm2",
            f"Ast,max                                ={astmax} mm2",
            f"Ast Governing                          ={max(astreq, astmin):.2f} mm2",
            f"No of Bars                             = {no_of_bars_bottom} No's ",
            f"Dia of Bars                            = {main_bar} mm",
            f" Bottom Reinforcement :- Provide {no_of_bars_top} no's of {main_bar} mm throughout the Bottom and {no_of_bars_bottom // 2} no's of {main_bar} mm curtail at L/3 from the face of the support",
            f"Ast,provided                           ={(main_bar * main_bar * 0.7857) * no_of_bars_top:.2f}",
            f"Percentage of steel                    ={pst:.3f} % "
            "Area of Steel Compression (Top Bars)- -  - - - - - - - - - - - - - - - - - - - - - - - ",
            f"Ast:-                                  ={astmin:.2f} mm2 ",
            f"Ast,min                                ={astmin:.2f} mm2",
            f"Ast,max                                ={astmax} mm2",
            f"Ast Governing                          ={max(astmin, astmin):.2f} mm2",
            f"No of Bars                             = {no_of_bars_top} No's",
            f"Dia of Bars                            = {top_bar} mm",
            f" Top Reinforcemnet :- Provide {no_of_bars_top} no's of {top_bar} mm throughout the top and {no_of_bars_bottom // 2} no's of {main_bar} mm curtail at L/3 from the face of the support",
            f"Ast,provived                           ={(dis_bar * dis_bar * 0.7857) * no_of_bars_top:.2f}",
            f"Percentage of steel                    ={plt:.3f} % ",
            "Check for Shear- -  - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - ",
            f"Tv                                  ={tv:.2f} N/mm2 ",
            f"Tc                                  ={tc:.2f} mm2",
            f"Tv <  Tc ,Section is Safe under Shear Force",
            f" Shear Reinforcemnet :- Provide {stdia} mm as vertical stirrups @ {max_spacing} mm c/c "
            "Check for Deflection- -  - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -",
            f"fs                                ={fs:.2f} N/mm2 ",
            f"Modification factor                 ={mf:.2f}",
            f"span/d limit                        ={20 * mf:.2f}",
            f"Actual span/d                      ={lef * 100 / effective_depth:.2f}",
            "Actual Span/d is greater than (span/d)limit , Hence Section is Safe under deflection"

            # Add more text as needed
        ]

        # Initial Y-coordinate
        y_location = width - overall_depth * 30

        # Loop through the text list
        for i, text_content in enumerate(texts):
            text_location = (
                xorigin + 6 * wall_thickness,  # X-coordinate remains constant
                y_location  # Y-coordinate decreases by overall_depth after each iteration
            )

            msp.add_text(
                text_content,
                dxfattribs={
                    'height': wall_thickness / 8,  # Text height
                    'layer': 'TEXT',  # Optional: specify a layer for the text
                    'color': 7,  # Optional: specify text color
                    'insert': text_location,  # X, Y coordinates
                }
            )

            # Decrease the Y-coordinate by overall_depth for the next text
            y_location -= overall_depth
        msp.add_line((xorigin + 5 * wall_thickness, width - overall_depth * 20),
                     (xorigin + 30 * wall_thickness, width - overall_depth * 20))
        msp.add_line((xorigin + 30 * wall_thickness, width - overall_depth * 20),
                     (xorigin + 30 * wall_thickness, y_location))
        msp.add_line((xorigin + 5 * wall_thickness, width - overall_depth * 20),
                     (xorigin + 5 * wall_thickness, y_location))
        msp.add_line((xorigin + 30 * wall_thickness, y_location),
                     (xorigin + 5 * wall_thickness, y_location))

        # project name
        msp.add_line((xorigin + 5 * wall_thickness, width - overall_depth * 25),
                     (xorigin + 30 * wall_thickness, width - overall_depth * 25))
        msp.add_line((xorigin + 5 * wall_thickness, width - overall_depth * 28),
                     (xorigin + 30 * wall_thickness, width - overall_depth * 28))
        msp.add_line((xorigin + 15 * wall_thickness, width - overall_depth * 22),
                     (xorigin + 30 * wall_thickness, width - overall_depth * 22))
        msp.add_line((xorigin + 10 * wall_thickness, width - overall_depth * 20),
                     (xorigin + 10 * wall_thickness, width - overall_depth * 28))
        msp.add_line((xorigin + 15 * wall_thickness, width - overall_depth * 20),
                     (xorigin + 15 * wall_thickness, width - overall_depth * 28))
        text_content = "Project :"
        text_location = (6 * wall_thickness + xorigin, width - 22.5 * overall_depth)

        msp.add_text(
            text_content,
            dxfattribs={
                'height': wall_thickness / 4,  # Text height
                'layer': 'TEXT',  # Optional: specify a layer for the text
                'color': 10,  # Optional: specify text color
                'insert': text_location,  # X, Y coordinates
            }
        )

        text_content = "Structure :"
        text_location = (6 * wall_thickness + xorigin, width - 26.5 * overall_depth)

        msp.add_text(
            text_content,
            dxfattribs={
                'height': wall_thickness / 4,  # Text height
                'layer': 'TEXT',  # Optional: specify a layer for the text
                'color': 7,  # Optional: specify text color
                'insert': text_location,  # X, Y coordinates
            }
        )

        text_content = "Designed :"
        text_location = (15.1 * wall_thickness + xorigin, width - 23 * overall_depth)

        msp.add_text(
            text_content,
            dxfattribs={
                'height': wall_thickness / 4,  # Text height
                'layer': 'TEXT',  # Optional: specify a layer for the text
                'color': 5,  # Optional: specify text color
                'insert': text_location,  # X, Y coordinates
            }
        )

        text_content = "Checked :"
        text_location = (15.1 * wall_thickness + xorigin, width - 25.5 * overall_depth)

        msp.add_text(
            text_content,
            dxfattribs={
                'height': wall_thickness / 4,  # Text height
                'layer': 'TEXT',  # Optional: specify a layer for the text
                'color': 3,  # Optional: specify text color
                'insert': text_location,  # X, Y coordinates
            }
        )
        today = datetime.today().strftime('%Y-%m-%d')
        text_content = f"Date: {today} "
        text_location = (15.1 * wall_thickness + xorigin, width - 21.5 * overall_depth)

        msp.add_text(
            text_content,
            dxfattribs={
                'height': wall_thickness / 6,  # Text height
                'layer': 'TEXT',  # Optional: specify a layer for the text
                'color': 21,  # Optional: specify text color
                'insert': text_location,  # X, Y coordinates
            }
        )


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
    elif (beam_type == "Fixed"):  # ----------------------------------------------simply supported-----------------------
        beam_length = float(request.form['beam_length'])
        clear_span = beam_length
        exposure_condition = request.form['exposure']
        wall_thickness = float(request.form['wall_thickness'])
        fck = int(request.form['fck'])
        fy = int(request.form['fy'])
        live_load = float(request.form['udl'])
        ll=live_load
        num_point_loads = 0
        point_loads = []
        print(beam_length)
        print(exposure_condition)
        print(wall_thickness)
        print(fck)
        print(fy)
        print(live_load)

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
            spant=spanratio
            d = l / spanratio  # Assuming the span/depth ratio is 15
            nominal_cover = get_nominal_cover(exposure_condition)
            print(d)
            effective_cover = nominal_cover + min_bar_dia + (max_bar_dia / 2)
            print("effective cover: ", effective_cover)
            overall_depth = round(d + effective_cover, -2)
            effective_depth = overall_depth - effective_cover
            return effective_depth, overall_depth, l, effective_cover, nominal_cover,spant

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
        effective_depth, overall_depth, l, effective_cover, nominal_cover,spant = get_effective_depth(clear_span,
                                                                                                wall_thickness,
                                                                                                exposure_condition,
                                                                                                min_bar_dia,
                                                                                                max_bar_dia)
        b = wall_thickness
        o_d = round(overall_depth, -2)
        print("Overall depth:", o_d)
        print("effective_depth: ", effective_depth)
        print("Assumed width of beam:", b)
        wtt=wall_thickness
        odt=o_d
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





        # Corrected annotations with proper facecolor specification
        live_load=live_load+o_d*wall_thickness*25/1000000
        max_bending_moment = live_load*beam_length*beam_length/12
        print("Maximum bending moment:", max_bending_moment, "kNm")
        ultimate_bending_moment = 1.5 * max_bending_moment
        print("Ultimate bending moment:", ultimate_bending_moment, "kNm")
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
            astt=ast
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
            pc = 100 * ab / (b * effective_depth)
            # print(main_bar, no_of_bars, pt)
            top_bar_provided = top_bar
            # no_of_bars = round(ast / (0.78539816339744830961566084581988 * main_bar ** 2), 0)
            print("Provide", no_of_bars_top, "-Φ", top_bar, " mm as main bars at the top")

            print("Percentage of steel provided(Compression Reinforcement): ", pc)
            #Side-face Reinforcement
            if o_d >= 750:
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



            print("modification factor: ", mf)
            if (allowablespan > Actualspan):
                print(" The section is safe under deflection")
            else:
                return(" revise section ,Section Fails under deflection")



        else:
            print("the section is over reinforced")
            ast1 = 0.00574712643678161 * (
                    87 * b * effective_depth * fck -
                    9.32737905308882 * (b * fck * (-400 * Ml + 87 * b * effective_depth ** 2 * fck)) ** 0.5
            ) / fy
            mu = ultimate_bending_moment
            ast2 = (mu - ml) * 10 ** 6 / (0.87 * fy * (effective_depth - effective_cover))
            ast = ast2 + ast1
            astt = ast
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

            if (astmin > ast):
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
                pc = 100 * ab / (b * effective_depth)
                # print(main_bar, no_of_bars, pt)
                top_bar_provided = top_bar
                print("provide", no_of_bars_top, "-Φ", top_bar, " mm as main bars at the top")

                print("percentage of steel provided(Compression Reinforcement): ", pc)
            else:
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
                pc = 100 * ab / (b * effective_depth)
                # print(main_bar, no_of_bars, pt)
                top_bar_provided = top_bar
                print("provide", no_of_bars_top, "-Φ", top_bar, " mm as main bars at the top")
                print("percentage of steel provided(Compression Reinforcement): ", pc)
            #side face
            if o_d >= 750:
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



            # print("modification factor: ", mf)
            if (allowablespan > Actualspan):
                print(" The section is safe under deflection")
            else:
                return(" revise section Section Fails under deflection")
        ast=max(ast,astmin)
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

        # column beam ld-----------------------------------------------------------------------------------------------------------
        msp.add_line((x, y - main_bar / 100),
                     (x, .6 * overall_depth))  # top left
        msp.add_line((x3, y3 + main_bar / 100), (x3, y4 + .4 * overall_depth))  # bottom left
        msp.add_line((x1, y1 - main_bar / 100), (x1, .6 * overall_depth))  # top left
        msp.add_line((x4, y4 + main_bar / 100), (x4, y4 + .4 * overall_depth))
        # ------------------top left join fillet
        attribs = {'layer': '0', 'color': 7}
        # top -left-----------------
        startleft_pointtl = (x + main_bar / 100, y)
        endleft_pointtl = (x, y - main_bar / 100)
        arctl = ConstructionArc.from_2p_radius(
            start_point=startleft_pointtl,
            end_point=endleft_pointtl,
            radius=main_bar / 100 + main_bar / 400  # left fillet
        )
        arctl.add_to_layout(msp, dxfattribs=attribs)
        # ------------------bot left join fillet
        attribs = {'layer': '0', 'color': 7}
        # bot -left-----------------
        startleft_pointbl = (x3, y3 + main_bar / 100)
        endleft_pointbl = (x3 + main_bar / 100, y3)
        arcbl = ConstructionArc.from_2p_radius(
            start_point=startleft_pointbl,
            end_point=endleft_pointbl,
            radius=main_bar / 100 + main_bar / 400  # left fillet
        )
        arcbl.add_to_layout(msp, dxfattribs=attribs)
        # top -right-----------------
        startleft_pointtl = (x1, y - main_bar / 100)
        endleft_pointtl = (x1 - main_bar / 100, y)
        arctl = ConstructionArc.from_2p_radius(
            start_point=startleft_pointtl,
            end_point=endleft_pointtl,
            radius=main_bar / 100 + main_bar / 400  # left fillet
        )
        arctl.add_to_layout(msp, dxfattribs=attribs)
        # ------------------bot left join fillet
        attribs = {'layer': '0', 'color': 7}
        # bot -right-----------------
        startleft_pointbl = (x4 - main_bar / 100, y3)
        endleft_pointbl = (x4, y3 + main_bar / 100)
        arcbl = ConstructionArc.from_2p_radius(
            start_point=startleft_pointbl,
            end_point=endleft_pointbl,
            radius=main_bar / 100 + main_bar / 400  # left fillet
        )
        arcbl.add_to_layout(msp, dxfattribs=attribs)
        # Create a Line
        msp.add_line((x + main_bar / 100, y), (x1 - main_bar / 100, y1))  # top bar
        msp.add_line((x3 + main_bar / 100, y3), (x4 - main_bar / 100, y4))  # bottom bar
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
        msp.add_line((0 + nominal_cover + main_bar / 100, -5 * overall_depth + nominal_cover),
                     (wall_thickness - nominal_cover - main_bar / 100,
                      -5 * overall_depth + nominal_cover))  # bottom line
        msp.add_line((0 + nominal_cover, -5 * overall_depth + nominal_cover + main_bar / 100),
                     (0 + nominal_cover, -4 * overall_depth - nominal_cover - top_bar / 100))  # left line
        msp.add_line((0 + nominal_cover + top_bar / 100, -4 * overall_depth - nominal_cover),
                     (wall_thickness - nominal_cover - top_bar / 100, -4 * overall_depth - nominal_cover))
        msp.add_line((wall_thickness - nominal_cover, -4 * overall_depth - nominal_cover - top_bar / 100),
                     (wall_thickness - nominal_cover, -5 * overall_depth + nominal_cover + main_bar / 100))
        # hook a-a----------------------------------
        attribs = {'layer': '0', 'color': 7}
        # bottom -left-----------------
        startleft_point = (nominal_cover, -5 * overall_depth + nominal_cover + main_bar / 100)
        endleft_point = (nominal_cover + main_bar / 100, -5 * overall_depth + nominal_cover)
        arc2 = ConstructionArc.from_2p_radius(
            start_point=startleft_point,
            end_point=endleft_point,
            radius=main_bar / 100 + main_bar / 400  # left fillet
        )
        arc2.add_to_layout(msp, dxfattribs=attribs)
        startleft_point = (
            wall_thickness - nominal_cover - main_bar / 100, -5 * overall_depth + nominal_cover)
        endleft_point = (
            wall_thickness - nominal_cover, -5 * overall_depth + nominal_cover + main_bar / 100)
        # bottom right
        arc2 = ConstructionArc.from_2p_radius(
            start_point=startleft_point,
            end_point=endleft_point,
            radius=main_bar / 100 + main_bar / 400  # left fillet
        )
        arc2.add_to_layout(msp, dxfattribs=attribs)
        # top right-------------------------------------
        endleft_point1 = (wall_thickness - nominal_cover - top_bar / 100, -4 * overall_depth - nominal_cover)
        startleft_point1 = (wall_thickness - nominal_cover, -4 * overall_depth - nominal_cover - top_bar / 100)
        arc3 = ConstructionArc.from_2p_radius(
            start_point=startleft_point1,
            end_point=endleft_point1,
            radius=top_bar / 100  # left fillet
        )
        arc3.add_to_layout(msp, dxfattribs=attribs)
        # top-left-----------------------------------------------------
        endleft_point2 = (1000 * clear_span - nominal_cover - top_bar / 100, -4 * overall_depth - nominal_cover)
        startleft_point2 = (1000 * clear_span - nominal_cover, -4 * overall_depth - nominal_cover - top_bar / 100)
        arc4 = ConstructionArc.from_2p_radius(
            start_point=startleft_point2,
            end_point=endleft_point2,
            radius=top_bar / 100  # left fillet
        )
        arc4.add_to_layout(msp, dxfattribs=attribs)
        # hook---------------------------------------
        msp.add_line((nominal_cover + top_bar / 100, -4 * overall_depth - nominal_cover), (
        nominal_cover + top_bar / 100 + 2 * top_bar / 100, -4 * overall_depth - nominal_cover - 2 * top_bar / 100))
        msp.add_line((nominal_cover, -4 * overall_depth - nominal_cover - top_bar / 100), (
        nominal_cover + 2 * top_bar / 100, -4 * overall_depth - nominal_cover - top_bar / 100 - 2 * top_bar / 100))
        # hook-fillet
        startleft_point3 = (nominal_cover + top_bar / 100, -4 * overall_depth - nominal_cover)
        endleft_point3 = (nominal_cover, -4 * overall_depth - nominal_cover - top_bar / 100)
        arc5 = ConstructionArc.from_2p_radius(
            start_point=startleft_point3,
            end_point=endleft_point3,
            radius=top_bar / 100  # left fillet
        )
        arc5.add_to_layout(msp, dxfattribs=attribs)
        #bottom bar- text------------------------A_A------------------------------
        X22 = clear_span * 1000
        X11 = clear_span

        text_content = f"{no_of_bars_bottom}-Y{main_bar} "
        text_location = (
            X11 + wall_thickness * 2, y4 - .55 * overall_depth)  # Positioning the text outside the rectangle
        dimstyle = msp.doc.dimstyles.get('EZDXF')  # Get the 'Standard' DIMSTYLE or create a new one
        dimstyle.dxf.dimasz = nominal_cover * 3
        msp.add_text(
            text_content,
            dxfattribs={
                'height': wall_thickness / 4,  # Text height
                'layer': 'TEXT',  # Optional: specify a layer for the text
                'color': 7,
                # Optional: specify text color
                'insert': text_location,  # Position of the text
            }
        )
        leader_points = [
            (X11 + wall_thickness, y4),  # Start inside the rectangle
            (X11 + wall_thickness, y4 - .5 * overall_depth),  # First bend point
            (X11 + 2 * wall_thickness, -.5 * overall_depth + y4)  # End point at the text location
        ]

        msp.add_leader(leader_points, dxfattribs={
            'color': 7,
            'dimstyle': 'EZDXF'})
        # -----top bar

        text_content = f"{no_of_bars_top}-Y{top_bar} + {no_bars_bottom//2}-Y{main_bar} "
        text_location = (
            X11 + wall_thickness * 2, 2 * overall_depth - y3 * 3)  # Positioning the text outside the rectangle
        dimstyle = msp.doc.dimstyles.get('EZDXF')  # Get the 'Standard' DIMSTYLE or create a new one
        dimstyle.dxf.dimasz = nominal_cover * 3
        msp.add_text(
            text_content,
            dxfattribs={
                'height': wall_thickness / 4,  # Text height
                'layer': 'TEXT',  # Optional: specify a layer for the text
                'color': 7,
                # Optional: specify text color
                'insert': text_location,  # Position of the text
            }
        )
        leader_points = [
            (X11 + wall_thickness, overall_depth - y3 * 1.5),  # Start inside the rectangle
            (X11 + wall_thickness, 2 * overall_depth - y3),  # First bend point
            (X11 + 2 * wall_thickness, 2 * overall_depth - y3)  # End point at the text location
        ]

        msp.add_leader(leader_points, dxfattribs={
            'color': 7,
            'dimstyle': 'EZDXF'})
        # ----striupp

        X6 = clear_span * 1000
        Y6 = overall_depth
        text_content = f"Y-{stdia} Stirrups @ {max_spacing} c/c"
        text_location = (
            X6 / 3 - wall_thickness, -1 * overall_depth)  # Positioning the text outside the rectangle
        dimstyle = msp.doc.dimstyles.get('EZDXF')  # Get the 'Standard' DIMSTYLE or create a new one
        dimstyle.dxf.dimasz = nominal_cover * 3
        msp.add_text(
            text_content,
            dxfattribs={
                'height': wall_thickness / 4,  # Text height
                'layer': 'TEXT',  # Optional: specify a layer for the text
                'color': 7,
                # Optional: specify text color
                'insert': text_location,  # Position of the text
            }
        )
        leader_points = [
            (X6 / 2, Y6 / 2),  # Start inside the rectangle
            (X6 / 2 - wall_thickness, Y6 / 2),  # First bend point
            (X6 / 2 - wall_thickness, Y6 * -1)  # End point at the text location
        ]

        msp.add_leader(leader_points, dxfattribs={
            'color': 7,
            'dimstyle': 'EZDXF'})
        # a-a ytext end-----------------------------------------------

        # b-b text start----------------------------------------------------------
        text_content = f"{no_of_bars_bottom}-Y{main_bar} + {no_of_bars_bottom//2}-Y{main_bar}  "
        text_location = (
            clear_span * 500 + wall_thickness,
            y4 - .55 * overall_depth)  # Positioning the text outside the rectangle
        dimstyle = msp.doc.dimstyles.get('EZDXF')  # Get the 'Standard' DIMSTYLE or create a new one
        dimstyle.dxf.dimasz = nominal_cover * 3
        msp.add_text(
            text_content,
            dxfattribs={
                'height': wall_thickness / 4,  # Text height
                'layer': 'TEXT',  # Optional: specify a layer for the text
                'color': 7,
                # Optional: specify text color
                'insert': text_location,  # Position of the text
            }
        )
        leader_points = [
            (clear_span * 500, y4),  # Start inside the rectangle
            (clear_span * 500, y4 - .5 * overall_depth),  # First bend point
            (clear_span * 500 + wall_thickness, -.5 * overall_depth + y4)  # End point at the text location
        ]

        msp.add_leader(leader_points, dxfattribs={
            'color': 7,
            'dimstyle': 'EZDXF'})
        # -----top bar

        text_content = f"{no_of_bars_top}-Y{top_bar} "
        text_location = (
            clear_span * 500 + wall_thickness,
            2.5 * overall_depth - y3 * 3)  # Positioning the text outside the rectangle
        dimstyle = msp.doc.dimstyles.get('EZDXF')  # Get the 'Standard' DIMSTYLE or create a new one
        dimstyle.dxf.dimasz = nominal_cover * 3
        msp.add_text(
            text_content,
            dxfattribs={
                'height': wall_thickness / 4,  # Text height
                'layer': 'TEXT',  # Optional: specify a layer for the text
                'color': 7,
                # Optional: specify text color
                'insert': text_location,  # Position of the text
            }
        )
        leader_points = [
            (clear_span * 500, overall_depth - y3 * 1.5),  # Start inside the rectangle
            (clear_span * 500, 2 * overall_depth - y3),  # First bend point
            (clear_span * 500 + wall_thickness, 2.5 * overall_depth - y3)  # End point at the text location
        ]

        msp.add_leader(leader_points, dxfattribs={
            'color': 7,
            'dimstyle': 'EZDXF'})
        # b-b- text end----------------------------------------------------------
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
        msp.add_line((500 * clear_span - nominal_cover - main_bar / 100, -5 * overall_depth + nominal_cover),
                     (500 * clear_span - wall_thickness + nominal_cover + main_bar / 100,
                      -5 * overall_depth + nominal_cover))  # bottom line
        msp.add_line(
            (500 * clear_span - wall_thickness + nominal_cover, -5 * overall_depth + nominal_cover + main_bar / 100),
            (500 * clear_span - wall_thickness + nominal_cover,
             -4 * overall_depth - nominal_cover - top_bar / 100))  # left line
        msp.add_line(
            (500 * clear_span - wall_thickness + nominal_cover + top_bar / 100, -4 * overall_depth - nominal_cover),
            (500 * clear_span - nominal_cover - top_bar / 100, -4 * overall_depth - nominal_cover))
        msp.add_line((500 * clear_span - nominal_cover, -4 * overall_depth - nominal_cover - top_bar / 100),
                     (500 * clear_span - nominal_cover, -5 * overall_depth + nominal_cover + main_bar / 100))
        # hook b-b
        attribs = {'layer': '0', 'color': 7}

        startleft_point = (
            500 * clear_span - wall_thickness + nominal_cover, -5 * overall_depth + nominal_cover + main_bar / 100)
        endleft_point = (
            500 * clear_span - wall_thickness + nominal_cover + main_bar / 100, -5 * overall_depth + nominal_cover)
        arc2 = ConstructionArc.from_2p_radius(
            start_point=startleft_point,
            end_point=endleft_point,
            radius=main_bar / 100 + main_bar / 400  # left fillet
        )
        arc2.add_to_layout(msp, dxfattribs=attribs)
        startleft_point = (
            500 * clear_span - wall_thickness + nominal_cover, -5 * overall_depth + nominal_cover + main_bar / 100)
        endleft_point = (
            500 * clear_span - wall_thickness + nominal_cover + main_bar / 100, -5 * overall_depth + nominal_cover)
        # bottom left
        arc2 = ConstructionArc.from_2p_radius(
            start_point=startleft_point,
            end_point=endleft_point,
            radius=main_bar / 100 + main_bar / 400  # left fillet
        )
        arc2.add_to_layout(msp, dxfattribs=attribs)
        # bottom right-------------------------------------
        endleft_point1 = (500 * clear_span - nominal_cover, -5 * overall_depth + nominal_cover + main_bar / 100)
        startleft_point1 = (500 * clear_span - nominal_cover - main_bar / 100, -5 * overall_depth + nominal_cover)
        arc3 = ConstructionArc.from_2p_radius(
            start_point=startleft_point1,
            end_point=endleft_point1,
            radius=main_bar / 100 + main_bar / 400  # left fillet
        )
        arc3.add_to_layout(msp, dxfattribs=attribs)
        # top-left-----------------------------------------------------
        endleft_point2 = (500 * clear_span - nominal_cover - top_bar / 100, -4 * overall_depth - nominal_cover)
        startleft_point2 = (500 * clear_span - nominal_cover, -4 * overall_depth - nominal_cover - top_bar / 100)
        arc4 = ConstructionArc.from_2p_radius(
            start_point=startleft_point2,
            end_point=endleft_point2,
            radius=top_bar / 100  # left fillet
        )
        arc4.add_to_layout(msp, dxfattribs=attribs)
        # hook---------------------------------------
        msp.add_line(
            (500 * clear_span - wall_thickness + nominal_cover + top_bar / 100, -4 * overall_depth - nominal_cover), (
                500 * clear_span - wall_thickness + nominal_cover + top_bar / 100 + 2 * top_bar / 100,
                -4 * overall_depth - nominal_cover - 2 * top_bar / 100))
        msp.add_line(
            (500 * clear_span - wall_thickness + nominal_cover, -4 * overall_depth - nominal_cover - top_bar / 100), (
                500 * clear_span - wall_thickness + nominal_cover + 2 * top_bar / 100,
                -4 * overall_depth - nominal_cover - top_bar / 100 - 2 * top_bar / 100))
        # hook-fillet
        startleft_point3 = (
            500 * clear_span - wall_thickness + nominal_cover + top_bar / 100, -4 * overall_depth - nominal_cover)
        endleft_point3 = (
            500 * clear_span - wall_thickness + nominal_cover, -4 * overall_depth - nominal_cover - top_bar / 100)
        arc5 = ConstructionArc.from_2p_radius(
            start_point=startleft_point3,
            end_point=endleft_point3,
            radius=top_bar / 100  # left fillet
        )
        arc5.add_to_layout(msp, dxfattribs=attribs)

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
        insert_point = (1000 * clear_span-wall_thickness, -7 * overall_depth)  # X, Y coordinates where the text will be inserted.
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
        msp.add_line((1000 * clear_span - nominal_cover - main_bar / 100, -5 * overall_depth + nominal_cover),
                     (1000 * clear_span - wall_thickness + nominal_cover + main_bar / 100,
                      -5 * overall_depth + nominal_cover))  # bottom line
        msp.add_line(
            (1000 * clear_span - wall_thickness + nominal_cover, -5 * overall_depth + nominal_cover + main_bar / 100),
            (1000 * clear_span - wall_thickness + nominal_cover,
             -4 * overall_depth - nominal_cover - top_bar / 100))  # left line
        msp.add_line(
            (1000 * clear_span - wall_thickness + nominal_cover + top_bar / 100, -4 * overall_depth - nominal_cover),
            (1000 * clear_span - nominal_cover - top_bar / 100, -4 * overall_depth - nominal_cover))
        msp.add_line((1000 * clear_span - nominal_cover, -4 * overall_depth - nominal_cover - top_bar / 100),
                     (1000 * clear_span - nominal_cover,
                      -5 * overall_depth + nominal_cover + main_bar / 100))  # right line



        attribs = {'layer': '0', 'color': 7}

        startleft_point = (
        1000 * clear_span - wall_thickness + nominal_cover, -5 * overall_depth + nominal_cover + main_bar / 100)
        endleft_point = (
        1000 * clear_span - wall_thickness + nominal_cover + main_bar / 100, -5 * overall_depth + nominal_cover)
        arc2 = ConstructionArc.from_2p_radius(
            start_point=startleft_point,
            end_point=endleft_point,
            radius=main_bar / 100 + main_bar / 400  # left fillet
        )
        arc2.add_to_layout(msp, dxfattribs=attribs)
        startleft_point = (
            1000 * clear_span - wall_thickness + nominal_cover, -5 * overall_depth + nominal_cover + main_bar / 100)
        endleft_point = (
            1000 * clear_span - wall_thickness + nominal_cover + main_bar / 100, -5 * overall_depth + nominal_cover)
        # bottom left
        arc2 = ConstructionArc.from_2p_radius(
            start_point=startleft_point,
            end_point=endleft_point,
            radius=main_bar / 100 + main_bar / 400  # left fillet
        )
        arc2.add_to_layout(msp, dxfattribs=attribs)
        # bottom right-------------------------------------
        endleft_point1 = (1000 * clear_span - nominal_cover, -5 * overall_depth + nominal_cover + main_bar / 100)
        startleft_point1 = (1000 * clear_span - nominal_cover - main_bar / 100, -5 * overall_depth + nominal_cover)
        arc3 = ConstructionArc.from_2p_radius(
            start_point=startleft_point1,
            end_point=endleft_point1,
            radius=main_bar / 100 + main_bar / 400  # left fillet
        )
        arc3.add_to_layout(msp, dxfattribs=attribs)
        # top-left-----------------------------------------------------
        endleft_point2 = (1000 * clear_span - nominal_cover - top_bar / 100, -4 * overall_depth - nominal_cover)
        startleft_point2 = (1000 * clear_span - nominal_cover, -4 * overall_depth - nominal_cover - top_bar / 100)
        arc4 = ConstructionArc.from_2p_radius(
            start_point=startleft_point2,
            end_point=endleft_point2,
            radius=top_bar / 100  # left fillet
        )
        arc4.add_to_layout(msp, dxfattribs=attribs)
        # hook---------------------------------------
        msp.add_line(
            (1000 * clear_span - wall_thickness + nominal_cover + top_bar / 100, -4 * overall_depth - nominal_cover), (
            1000 * clear_span - wall_thickness + nominal_cover + top_bar / 100 + 2 * top_bar / 100,
            -4 * overall_depth - nominal_cover - 2 * top_bar / 100))
        msp.add_line(
            (1000 * clear_span - wall_thickness + nominal_cover, -4 * overall_depth - nominal_cover - top_bar / 100), (
            1000 * clear_span - wall_thickness + nominal_cover + 2 * top_bar / 100,
            -4 * overall_depth - nominal_cover - top_bar / 100 - 2 * top_bar / 100))
        # hook-fillet
        startleft_point3 = (
        1000 * clear_span - wall_thickness + nominal_cover + top_bar / 100, -4 * overall_depth - nominal_cover)
        endleft_point3 = (
        1000 * clear_span - wall_thickness + nominal_cover, -4 * overall_depth - nominal_cover - top_bar / 100)
        arc5 = ConstructionArc.from_2p_radius(
            start_point=startleft_point3,
            end_point=endleft_point3,
            radius=top_bar / 100  # left fillet
        )
        arc5.add_to_layout(msp, dxfattribs=attribs)

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
                    #----------------------------------------extra rods
        xe = -wall_thickness + nominal_cover+wall_thickness/2
        ye = overall_depth - nominal_cover * 2
        x1e = clear_span * 200+50*top_bar_provided/100
        y1e = overall_depth - nominal_cover * 2
        x3e = clear_span*1000+wall_thickness-nominal_cover-wall_thickness/2
        y3e = o_d / 100 - nominal_cover * 2
        x4e = clear_span * 800 - 50 * top_bar_provided / 100
        y4e = o_d / 100 - nominal_cover * 2
        dim3 = msp.add_linear_dim(
            base=(150*clear_span, 1.1 * overall_depth),  # location of the dimension line
            p1=(0, overall_depth-nominal_cover/100),  # 1st measurement point
            p2=(x1e, overall_depth-nominal_cover/100),  # 2nd measurement point
            dimstyle="EZDXF",  # default dimension style
        )
        dim3 = msp.add_linear_dim(
            base=(500 * clear_span, 1.1 * overall_depth),  # location of the dimension line
            p1=(x4e, overall_depth - nominal_cover / 100),  # 1st measurement point
            p2=(x1e, overall_depth - nominal_cover / 100),  # 2nd measurement point
            dimstyle="EZDXF",  # default dimension style
        )
        dim3 = msp.add_linear_dim(
            base=(750 * clear_span, 1.1 * overall_depth),  # location of the dimension line
            p1=(x4e, overall_depth - nominal_cover / 100),  # 1st measurement point
            p2=(x3e-wall_thickness/2+nominal_cover, overall_depth - nominal_cover / 100),  # 2nd measurement point
            dimstyle="EZDXF",  # default dimension style
        )


        # Create a Line
        msp.add_line((xe, o_d/100-nominal_cover*2), (x1e, o_d/100-nominal_cover*2))  # top bar
        msp.add_line((x1e, o_d/100-nominal_cover*2),(x1e+nominal_cover,o_d/100-nominal_cover*4))
        msp.add_line((x3e, y3e), (x4e, y4e))#top left
        msp.add_line((x4e-nominal_cover,o_d/100 -nominal_cover*4),(x4e,y4e))
        msp.add_line((x1e,2*nominal_cover),(x4e,2*nominal_cover))#bottom extra
        msp.add_line((x1e , 2 * nominal_cover),
                     (x1e -nominal_cover, 4*nominal_cover))  # bottom extra
        msp.add_line((x4e, 2 * nominal_cover),
                     (x4e  + nominal_cover, 4 * nominal_cover))
        #------------------------------------------------------------extra rod
    #column beam ld-----------------------------------------------------------------------------------------------------------
        msp.add_line((-wall_thickness + nominal_cover / 100,overall_depth - nominal_cover ),(-wall_thickness + nominal_cover / 100,overall_depth*.25 - nominal_cover ))
        # -----------------------------------------------------------------BBS---------------------------------------------

        start_x = 0
        start_y = -8 * o_d / 100
        cell_width = wall_thickness * 3
        cell_height = wall_thickness
        header_height = 2 * wall_thickness
        print(
            'bbs-------------------------------------------------------------------------------------------------------------------------------------------')
        # -----------------------cutting lenth top bar---------------------------
        cut_top_bar = round(clear_span * 100000 + 2 * 50 * top_bar - 2 * nominal_cover * 100, 3)
        cut_bot_bar = round(clear_span * 100000 + 2 * 50 * main_bar - 2 * nominal_cover * 100, 3)
        print(cut_top_bar)
        print(cut_bot_bar)
        print(no_of_bars_top)
        # bar shape text--------------------------------------------------------
        bar_string = "a"
        insert_point = (
            2 * cell_width * .9, start_y - cell_height * 2.5)  # X, Y coordinates where the text will be inserted.
        text_height = .5
        # Add text to the modelspace.
        msp.add_text(
            bar_string,
            dxfattribs={
                'insert': insert_point,
                'height': text_height,
                # Additional attributes such as font, rotation, and color can be specified here.
                'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                'rotation': 0,
                'color': 7
            }
        )
        bar_string = "b"
        insert_point = (
            1.5 * cell_width, start_y - cell_height * 2.5)  # X, Y coordinates where the text will be inserted.
        text_height = .5
        # Add text to the modelspace.
        msp.add_text(
            bar_string,
            dxfattribs={
                'insert': insert_point,
                'height': text_height,
                # Additional attributes such as font, rotation, and color can be specified here.
                'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                'rotation': 0,
                'color': 7
            }
        )
        bar_string = "Top Bar"
        insert_point = (
            .1 * cell_width, start_y - cell_height * 2.5)  # X, Y coordinates where the text will be inserted.
        text_height = .5
        # Add text to the modelspace.
        msp.add_text(
            bar_string,
            dxfattribs={
                'insert': insert_point,
                'height': text_height,
                # Additional attributes such as font, rotation, and color can be specified here.
                'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                'rotation': 0,
                'color': 7
            }
        )
        a_top = 50 * top_bar
        bar_string = str(a_top / 1000)
        insert_point = (
            2.5 * cell_width, start_y - cell_height * 2.5)  # X, Y coordinates where the text will be inserted.
        text_height = .5
        # Add text to the modelspace.
        msp.add_text(
            bar_string,
            dxfattribs={
                'insert': insert_point,
                'height': text_height,
                # Additional attributes such as font, rotation, and color can be specified here.
                'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                'rotation': 0,
                'color': 7
            }
        )

        bar_string = "Nil"
        insert_point = (
            4.5 * cell_width, start_y - cell_height * 2.5)  # X, Y coordinates where the text will be inserted.
        text_height = .5
        # Add text to the modelspace.
        msp.add_text(
            bar_string,
            dxfattribs={
                'insert': insert_point,
                'height': text_height,
                # Additional attributes such as font, rotation, and color can be specified here.
                'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                'rotation': 0,
                'color': 7
            }
        )
        b_top = clear_span * 100
        bar_string = str(b_top)
        insert_point = (
            3.5 * cell_width, start_y - cell_height * 2.5)  # X, Y coordinates where the text will be inserted.
        text_height = .5
        # Add text to the modelspace.
        msp.add_text(
            bar_string,
            dxfattribs={
                'insert': insert_point,
                'height': text_height,
                # Additional attributes such as font, rotation, and color can be specified here.
                'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                'rotation': 0,
                'color': 7
            }
        )
        b_top = top_bar
        bar_string = str(b_top)
        insert_point = (
            5.5 * cell_width, start_y - cell_height * 2.5)  # X, Y coordinates where the text will be inserted.
        text_height = .5
        # Add text to the modelspace.
        msp.add_text(
            bar_string,
            dxfattribs={
                'insert': insert_point,
                'height': text_height,
                # Additional attributes such as font, rotation, and color can be specified here.
                'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                'rotation': 0,
                'color': 7
            }
        )
        bar_string = "Nil"
        insert_point = (
            6.5 * cell_width, start_y - cell_height * 2.5)  # X, Y coordinates where the text will be inserted.
        text_height = .5
        # Add text to the modelspace.
        msp.add_text(
            bar_string,
            dxfattribs={
                'insert': insert_point,
                'height': text_height,
                # Additional attributes such as font, rotation, and color can be specified here.
                'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                'rotation': 0,
                'color': 7
            }
        )
        # row 1 end---------------------------------------------------------------------------------------------------------------------------------------------row-1 end
        # row2------------------------row -2 -------------------------------------------------- row -2
        bar_string = "a"
        insert_point = (
            2 * cell_width * .95, start_y - cell_height * 3.6)  # X, Y coordinates where the text will be inserted.
        text_height = .5
        # Add text to the modelspace.
        msp.add_text(
            bar_string,
            dxfattribs={
                'insert': insert_point,
                'height': text_height,
                # Additional attributes such as font, rotation, and color can be specified here.
                'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                'rotation': 0,
                'color': 7
            }
        )
        bar_string = "b"
        insert_point = (
            1.5 * cell_width, start_y - cell_height * 3.5)  # X, Y coordinates where the text will be inserted.
        text_height = .5
        # Add text to the modelspace.
        msp.add_text(
            bar_string,
            dxfattribs={
                'insert': insert_point,
                'height': text_height,
                # Additional attributes such as font, rotation, and color can be specified here.
                'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                'rotation': 0,
                'color': 7
            }
        )
        bar_string = "Bottom Bar"
        insert_point = (
            .1 * cell_width, start_y - cell_height * 3.5)  # X, Y coordinates where the text will be inserted.
        text_height = .5
        # Add text to the modelspace.
        msp.add_text(
            bar_string,
            dxfattribs={
                'insert': insert_point,
                'height': text_height,
                # Additional attributes such as font, rotation, and color can be specified here.
                'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                'rotation': 0,
                'color': 7
            }
        )
        a_top = 50 * main_bar
        bar_string = str(a_top / 1000)
        insert_point = (
            2.5 * cell_width, start_y - cell_height * 3.5)  # X, Y coordinates where the text will be inserted.
        text_height = .5
        # Add text to the modelspace.
        msp.add_text(
            bar_string,
            dxfattribs={
                'insert': insert_point,
                'height': text_height,
                # Additional attributes such as font, rotation, and color can be specified here.
                'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                'rotation': 0,
                'color': 7
            }
        )

        bar_string = "Nil"
        insert_point = (
            4.5 * cell_width, start_y - cell_height * 3.5)  # X, Y coordinates where the text will be inserted.
        text_height = .5
        # Add text to the modelspace.
        msp.add_text(
            bar_string,
            dxfattribs={
                'insert': insert_point,
                'height': text_height,
                # Additional attributes such as font, rotation, and color can be specified here.
                'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                'rotation': 0,
                'color': 7
            }
        )
        b_top = clear_span * 100
        bar_string = str(b_top)
        insert_point = (
            3.5 * cell_width, start_y - cell_height * 3.5)  # X, Y coordinates where the text will be inserted.
        text_height = .5
        # Add text to the modelspace.
        msp.add_text(
            bar_string,
            dxfattribs={
                'insert': insert_point,
                'height': text_height,
                # Additional attributes such as font, rotation, and color can be specified here.
                'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                'rotation': 0,
                'color': 7
            }
        )
        b_top = main_bar
        bar_string = str(b_top)
        insert_point = (
            5.5 * cell_width, start_y - cell_height * 3.5)  # X, Y coordinates where the text will be inserted.
        text_height = .5
        # Add text to the modelspace.
        msp.add_text(
            bar_string,
            dxfattribs={
                'insert': insert_point,
                'height': text_height,
                # Additional attributes such as font, rotation, and color can be specified here.
                'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                'rotation': 0,
                'color': 7
            }
        )
        bar_string = "Nil"
        insert_point = (
            6.5 * cell_width, start_y - cell_height * 3.5)  # X, Y coordinates where the text will be inserted.
        text_height = .5
        # Add text to the modelspace.
        msp.add_text(
            bar_string,
            dxfattribs={
                'insert': insert_point,
                'height': text_height,
                # Additional attributes such as font, rotation, and color can be specified here.
                'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                'rotation': 0,
                'color': 7
            }
        )
        # text insert for cutting length top-----------------------------
        top_string = str(cut_top_bar / 1000)
        insert_point = (
        7 * cell_width + .8, start_y - cell_height * 3 + .5)  # X, Y coordinates where the text will be inserted.
        text_height = 1
        # Add text to the modelspace.
        msp.add_text(
            top_string,
            dxfattribs={
                'insert': insert_point,
                'height': text_height,
                # Additional attributes such as font, rotation, and color can be specified here.
                'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                'rotation': 0,
                'color': 7
            }
        )
        # number of bars ---------------------------------------------------

        top_string = str(no_of_bars_top)
        insert_point = (
            8 * cell_width + .8, start_y - cell_height * 3 + .5)  # X, Y coordinates where the text will be inserted.
        text_height = 1
        # Add text to the modelspace.
        msp.add_text(
            top_string,
            dxfattribs={
                'insert': insert_point,
                'height': text_height,
                # Additional attributes such as font, rotation, and color can be specified here.
                'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                'rotation': 0,
                'color': 7
            }
        )
        # striupp-----------------------------------------------------------------------------------------------------
        bar_string = "c"
        insert_point = (
            2 * cell_width * .6, start_y - cell_height * 4.6)  # X, Y coordinates where the text will be inserted.
        text_height = .5
        # Add text to the modelspace.
        msp.add_text(
            bar_string,
            dxfattribs={
                'insert': insert_point,
                'height': text_height,
                # Additional attributes such as font, rotation, and color can be specified here.
                'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                'rotation': 0,
                'color': 7
            }
        )
        bar_string = "a"
        insert_point = (
            1.5 * cell_width, start_y - cell_height * 4.5)  # X, Y coordinates where the text will be inserted.
        text_height = .5
        # Add text to the modelspace.
        msp.add_text(
            bar_string,
            dxfattribs={
                'insert': insert_point,
                'height': text_height,
                # Additional attributes such as font, rotation, and color can be specified here.
                'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                'rotation': 0,
                'color': 7
            }
        )
        bar_string = "Stirrup"
        insert_point = (
            .1 * cell_width, start_y - cell_height * 4.5)  # X, Y coordinates where the text will be inserted.
        text_height = .5
        # Add text to the modelspace.
        msp.add_text(
            bar_string,
            dxfattribs={
                'insert': insert_point,
                'height': text_height,
                # Additional attributes such as font, rotation, and color can be specified here.
                'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                'rotation': 0,
                'color': 7
            }
        )
        a_top = round(wall_thickness * 100 - 200 * nominal_cover,3)
        print(a_top,"atop")
        bar_string = str(a_top / 1000)
        insert_point = (
            2.5 * cell_width, start_y - cell_height * 4.5)  # X, Y coordinates where the text will be inserted.
        text_height = .5
        # Add text to the modelspace.
        msp.add_text(
            bar_string,
            dxfattribs={
                'insert': insert_point,
                'height': text_height,
                # Additional attributes such as font, rotation, and color can be specified here.
                'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                'rotation': 0,
                'color': 7
            }
        )
        st_dep = round(o_d - 200 * nominal_cover,3)
        bar_string = str(st_dep / 1000)
        insert_point = (
            4.5 * cell_width, start_y - cell_height * 4.5)  # X, Y coordinates where the text will be inserted.
        text_height = .5
        # Add text to the modelspace.
        msp.add_text(
            bar_string,
            dxfattribs={
                'insert': insert_point,
                'height': text_height,
                # Additional attributes such as font, rotation, and color can be specified here.
                'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                'rotation': 0,
                'color': 7
            }
        )

        bar_string = "Nil"
        insert_point = (
            3.5 * cell_width, start_y - cell_height * 4.5)  # X, Y coordinates where the text will be inserted.
        text_height = .5
        # Add text to the modelspace.
        msp.add_text(
            bar_string,
            dxfattribs={
                'insert': insert_point,
                'height': text_height,
                # Additional attributes such as font, rotation, and color can be specified here.
                'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                'rotation': 0,
                'color': 7
            }
        )
        b_top = stdia
        bar_string = str(b_top)
        insert_point = (
            5.5 * cell_width, start_y - cell_height * 4.5)  # X, Y coordinates where the text will be inserted.
        text_height = .5
        # Add text to the modelspace.
        msp.add_text(
            bar_string,
            dxfattribs={
                'insert': insert_point,
                'height': text_height,
                # Additional attributes such as font, rotation, and color can be specified here.
                'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                'rotation': 0,
                'color': 7
            }
        )
        b_top = round(2 * (10 * stdia / 1000 + st_dep / 1000 + a_top / 1000-3*stdia/1000)-2*5*stdia/1000, 3)
        stirrup_cut_length = b_top
        bar_string = str(b_top)
        insert_point = (
            7.1 * cell_width , start_y - cell_height * 4.9)  # X, Y coordinates where the text will be inserted.
        text_height = 1
        # Add text to the modelspace.
        msp.add_text(
            bar_string,
            dxfattribs={
                'insert': insert_point,
                'height': text_height,
                # Additional attributes such as font, rotation, and color can be specified here.
                'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                'rotation': 0,
                'color': 7
            }
        )
        bar_string = str(max_spacing)
        insert_point = (
            6.5 * cell_width, start_y - cell_height * 4.5)  # X, Y coordinates where the text will be inserted.
        text_height = .5
        # Add text to the modelspace.
        msp.add_text(
            bar_string,
            dxfattribs={
                'insert': insert_point,
                'height': text_height,
                # Additional attributes such as font, rotation, and color can be specified here.
                'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                'rotation': 0,
                'color': 7
            }
        )
        no_str = math.ceil(clear_span * 100000 / max_spacing + 1)

        top_string = str(no_str)
        insert_point = (
            8 * cell_width + .8, start_y - cell_height * 5 + .5)  # X, Y coordinates where the text will be inserted.
        text_height = 1
        # Add text to the modelspace.
        msp.add_text(
            top_string,
            dxfattribs={
                'insert': insert_point,
                'height': text_height,
                # Additional attributes such as font, rotation, and color can be specified here.
                'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                'rotation': 0,
                'color': 7
            }
        )
        # stirru shape------------------------------------------------------------
        msp.add_line((1.3 * cell_width, start_y - cell_height * 5 + .5),
                     (1.6 * cell_width, start_y - cell_height * 5 + .5))
        msp.add_line((1.3 * cell_width, start_y - cell_height * 4.5 + .5),
                     (1.3 * cell_width, start_y - cell_height * 5 + .5))
        msp.add_line((1.6 * cell_width, start_y - cell_height * 4.5 + .5),
                     (1.6 * cell_width, start_y - cell_height * 5 + .5))
        msp.add_line((1.3 * cell_width, start_y - cell_height * 4.5 + .5),
                     (1.6 * cell_width, start_y - cell_height * 4.5 + .5))
        # hook--------------------------------------------------------------------------------------
        msp.add_line((1.3 * cell_width, start_y - cell_height * 4.5 + .45),
                     (1.3 * cell_width + .4, start_y - cell_height * 4.5 - .25))
        msp.add_line((1.3 * cell_width + .4, start_y - cell_height * 4.5 + .5),
                     (1.3 * cell_width + .8, start_y - cell_height * 4.5))
        # striupp end
        # dia with total length-----------------------------------------------------------------------------------------------------------------------

        # text insert for cutting length top-----------------------------
        top_string = str(cut_top_bar / 1000)
        cut_length_top = cut_top_bar / 1000
        insert_point = (
            7 * cell_width + .8, start_y - cell_height * 3 + .5)  # X, Y coordinates where the text will be inserted.
        text_height = 1
        # Add text to the modelspace.
        msp.add_text(
            top_string,
            dxfattribs={
                'insert': insert_point,
                'height': text_height,
                # Additional attributes such as font, rotation, and color can be specified here.
                'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                'rotation': 0,
                'color': 7
            }
        )
        # number of bars ---------------------------------------------------
        top_string = str(no_of_bars_top)
        print("t", no_of_bars_top)
        insert_point = (
            8 * cell_width + .8, start_y - cell_height * 3 + .5)  # X, Y coordinates where the text will be inserted.
        text_height = 1
        # Add text to the modelspace.
        msp.add_text(
            top_string,
            dxfattribs={
                'insert': insert_point,
                'height': text_height,
                # Additional attributes such as font, rotation, and color can be specified here.
                'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                'rotation': 0,
                'color': 7
            }
        )

        # bottom bar-------------------------------------------------------------------------------
        msp.add_line((1.2 * cell_width, start_y - cell_height * 4 + .5),
                     (1.8 * cell_width, start_y - cell_height * 4 + .5))
        msp.add_line((1.2 * cell_width, start_y - cell_height * 3.5 + .5),
                     (1.2 * cell_width, start_y - cell_height * 4 + .5))
        msp.add_line((1.8 * cell_width, start_y - cell_height * 3.5 + .5),
                     (1.8 * cell_width, start_y - cell_height * 4 + .5))
        bot_string = str(cut_bot_bar / 1000)
        cut_length_bottom = cut_bot_bar / 1000
        insert_point = (
            7 * cell_width + .8, start_y - cell_height * 4 + .5)  # X, Y coordinates where the text will be inserted.
        text_height = 1
        # Add text to the modelspace.
        msp.add_text(
            bot_string,
            dxfattribs={
                'insert': insert_point,
                'height': text_height,
                # Additional attributes such as font, rotation, and color can be specified here.
                'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                'rotation': 0,
                'color': 7
            }
        )
        # number of bottom bars
        bot_string = str(no_of_bars_bottom)
        insert_point = (
            8 * cell_width + .8, start_y - cell_height * 4 + .5)  # X, Y coordinates where the text will be inserted.
        text_height = 1
        # Add text to the modelspace.
        msp.add_text(
            bot_string,
            dxfattribs={
                'insert': insert_point,
                'height': text_height,
                # Additional attributes such as font, rotation, and color can be specified here.
                'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                'rotation': 0,
                'color': 7
            }
        )

        # Column headers
        msp.add_line((9 * cell_width, start_y), (9 * cell_width, start_y + cell_height))
        msp.add_line((17 * cell_width, start_y), (17 * cell_width, start_y + cell_height))
        msp.add_line((9 * cell_width, start_y + cell_height), (17 * cell_width, start_y + cell_height))
        # weight calculation----------------------------------------------------------------------------------

        msp.add_line((9 * cell_width, start_y - 10 * cell_height), (9 * cell_width, start_y - 5 * cell_height))
        msp.add_line((10 * cell_width, start_y - 9 * cell_height), (10 * cell_width, start_y - 5 * cell_height))
        msp.add_line((11 * cell_width, start_y - 9 * cell_height), (11 * cell_width, start_y - 5 * cell_height))
        msp.add_line((12 * cell_width, start_y - 9 * cell_height), (12 * cell_width, start_y - 5 * cell_height))
        msp.add_line((13 * cell_width, start_y - 9 * cell_height), (13 * cell_width, start_y - 5 * cell_height))
        msp.add_line((14 * cell_width, start_y - 9 * cell_height), (14 * cell_width, start_y - 5 * cell_height))
        msp.add_line((15 * cell_width, start_y - 9 * cell_height), (15 * cell_width, start_y - 5 * cell_height))
        msp.add_line((16 * cell_width, start_y - 9 * cell_height), (16 * cell_width, start_y - 5 * cell_height))
        msp.add_line((17 * cell_width, start_y - 10 * cell_height), (17 * cell_width, start_y - 5 * cell_height))
        msp.add_line((6 * cell_width, start_y - 10 * cell_height), (6 * cell_width, start_y - 5 * cell_height))
        msp.add_line((17 * cell_width, start_y - 9 * cell_height), (17 * cell_width, start_y - 5 * cell_height))
        msp.add_line((6 * cell_width, start_y - 10 * cell_height), (17 * cell_width, start_y - 10 * cell_height))
        bot_string = "Total reinforcement Weight in Kg's"
        insert_point = (
        6.1 * cell_width, start_y - 9.5 * cell_height)  # X, Y coordinates where the text will be inserted.
        text_height = .8
        # Add text to the modelspace.
        msp.add_text(
            bot_string,
            dxfattribs={
                'insert': insert_point,
                'height': text_height,
                # Additional attributes such as font, rotation, and color can be specified here.
                'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                'rotation': 0,
                'color': 7
            }
        )
        msp.add_line((6 * cell_width, start_y - 9 * cell_height), (17 * cell_width, start_y - 9 * cell_height))
        bot_string = " Weight in Kg's"
        insert_point = (
            6.1 * cell_width, start_y - 8.5 * cell_height)  # X, Y coordinates where the text will be inserted.
        text_height = .8
        # Add text to the modelspace.
        msp.add_text(
            bot_string,
            dxfattribs={
                'insert': insert_point,
                'height': text_height,
                # Additional attributes such as font, rotation, and color can be specified here.
                'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                'rotation': 0,
                'color': 7
            }
        )
        msp.add_line((6 * cell_width, start_y - 8 * cell_height), (17 * cell_width, start_y - 8 * cell_height))
        bot_string = "Unit Weight in Kg/m"
        insert_point = (
            6.1 * cell_width, start_y - 7.5 * cell_height)  # X, Y coordinates where the text will be inserted.
        text_height = .8
        # Add text to the modelspace.
        msp.add_text(
            bot_string,
            dxfattribs={
                'insert': insert_point,
                'height': text_height,
                # Additional attributes such as font, rotation, and color can be specified here.
                'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                'rotation': 0,
                'color': 7
            }
        )
        msp.add_line((6 * cell_width, start_y - 7 * cell_height), (17 * cell_width, start_y - 7 * cell_height))
        bot_string = "Total length (m)"
        insert_point = (
            6.1 * cell_width, start_y - 6.5 * cell_height)  # X, Y coordinates where the text will be inserted.
        text_height = .8
        # Add text to the modelspace.
        msp.add_text(
            bot_string,
            dxfattribs={
                'insert': insert_point,
                'height': text_height,
                # Additional attributes such as font, rotation, and color can be specified here.
                'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                'rotation': 0,
                'color': 7
            }
        )
        st_length = round(stirrup_cut_length * no_str, 3)
        dia_string = str(st_length)
        insert_point = (
            9.1 * cell_width,
            start_y - cell_height * 6.9)  # X, Y coordinates where the text will be inserted.
        text_height = 1
        # Add text to the modelspace.
        msp.add_text(
            dia_string,
            dxfattribs={
                'insert': insert_point,
                'height': text_height,
                # Additional attributes such as font, rotation, and color can be specified here.
                'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                'rotation': 0,
                'color': 7
            }
        )
        if (top_bar == 12 and main_bar == 12):
            bot_length = round(cut_length_bottom * no_bars_bottom, 3) + round(cut_length_top * no_of_bars_top, 3)
            dia_string = str(round(bot_length,3))
            insert_point = (
                11.1 * cell_width,
                start_y - cell_height * 6.9)  # X, Y coordinates where the text will be inserted.
            text_height = 1
            # Add text to the modelspace.
            msp.add_text(
                dia_string,
                dxfattribs={
                    'insert': insert_point,
                    'height': text_height,
                    # Additional attributes such as font, rotation, and color can be specified here.
                    'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                    'rotation': 0,
                    'color': 7
                }
            )
            bot_length = round(cut_length_bottom * no_bars_bottom, 3) + round(cut_length_top * no_of_bars_top, 3)
            dia_string = str(round(bot_length * .889, 3))
            insert_point = (
                11.1 * cell_width,
                start_y - cell_height * 8.9)  # X, Y coordinates where the text will be inserted.
            text_height = 1
            # Add text to the modelspace.
            msp.add_text(
                dia_string,
                dxfattribs={
                    'insert': insert_point,
                    'height': text_height,
                    # Additional attributes such as font, rotation, and color can be specified here.
                    'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                    'rotation': 0,
                    'color': 7
                }
            )
        if (top_bar == 16 and main_bar == 16):
            bot_length = round(cut_length_bottom * no_bars_bottom, 3) + round(cut_length_top * no_of_bars_top, 3)
            dia_string = str(round(bot_length,3))
            insert_point = (
                12.1 * cell_width,
                start_y - cell_height * 6.9)  # X, Y coordinates where the text will be inserted.
            text_height = 1
            # Add text to the modelspace.
            msp.add_text(
                dia_string,
                dxfattribs={
                    'insert': insert_point,
                    'height': text_height,
                    # Additional attributes such as font, rotation, and color can be specified here.
                    'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                    'rotation': 0,
                    'color': 7
                }
            )
            bot_length = round(cut_length_bottom * no_bars_bottom, 3) + round(cut_length_top * no_of_bars_top, 3)
            dia_string = str(round(bot_length * 1.578, ))
            insert_point = (
                12.1 * cell_width,
                start_y - cell_height * 8.9)  # X, Y coordinates where the text will be inserted.
            text_height = 1
            # Add text to the modelspace.
            msp.add_text(
                dia_string,
                dxfattribs={
                    'insert': insert_point,
                    'height': text_height,
                    # Additional attributes such as font, rotation, and color can be specified here.
                    'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                    'rotation': 0,
                    'color': 7
                }
            )
        if (top_bar == 20 and main_bar == 20):
            bot_length = round(cut_length_bottom * no_bars_bottom, 3) + round(cut_length_top * no_of_bars_top, 3)
            dia_string = str(round(bot_length,3))
            insert_point = (
                13.1 * cell_width,
                start_y - cell_height * 6.9)  # X, Y coordinates where the text will be inserted.
            text_height = 1
            # Add text to the modelspace.
            msp.add_text(
                dia_string,
                dxfattribs={
                    'insert': insert_point,
                    'height': text_height,
                    # Additional attributes such as font, rotation, and color can be specified here.
                    'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                    'rotation': 0,
                    'color': 7
                }
            )
            bot_length = round(cut_length_bottom * no_bars_bottom, 3) + round(cut_length_top * no_of_bars_top, 3)
            dia_string = str(round(bot_length * 2.469, 3))
            insert_point = (
                13.1 * cell_width,
                start_y - cell_height * 8.9)  # X, Y coordinates where the text will be inserted.
            text_height = 1
            # Add text to the modelspace.
            msp.add_text(
                dia_string,
                dxfattribs={
                    'insert': insert_point,
                    'height': text_height,
                    # Additional attributes such as font, rotation, and color can be specified here.
                    'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                    'rotation': 0,
                    'color': 7
                }
            )
        if (top_bar == 25 and main_bar == 25):
            bot_length = round(cut_length_bottom * no_bars_bottom, 3) + round(cut_length_top * no_of_bars_top, 3)
            dia_string = str(round(bot_length,3))
            insert_point = (
                14.1 * cell_width,
                start_y - cell_height * 6.9)  # X, Y coordinates where the text will be inserted.
            text_height = 1
            # Add text to the modelspace.
            msp.add_text(
                dia_string,
                dxfattribs={
                    'insert': insert_point,
                    'height': text_height,
                    # Additional attributes such as font, rotation, and color can be specified here.
                    'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                    'rotation': 0,
                    'color': 7
                }
            )
            bot_length = round(cut_length_bottom * no_bars_bottom, 3) + round(cut_length_top * no_of_bars_top, 3)
            dia_string = str(round(bot_length * 3.858, 3))
            insert_point = (
                14.1 * cell_width,
                start_y - cell_height * 8.9)  # X, Y coordinates where the text will be inserted.
            text_height = 1
            # Add text to the modelspace.
            msp.add_text(
                dia_string,
                dxfattribs={
                    'insert': insert_point,
                    'height': text_height,
                    # Additional attributes such as font, rotation, and color can be specified here.
                    'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                    'rotation': 0,
                    'color': 7
                }
            )
        if (top_bar == 32 and main_bar == 32):
            bot_length = round(cut_length_bottom * no_bars_bottom, 3) + round(cut_length_top * no_of_bars_top, 3)
            dia_string = str(round(bot_length,3))
            insert_point = (
                15.1 * cell_width,
                start_y - cell_height * 6.9)  # X, Y coordinates where the text will be inserted.
            text_height = 1
            # Add text to the modelspace.
            msp.add_text(
                dia_string,
                dxfattribs={
                    'insert': insert_point,
                    'height': text_height,
                    # Additional attributes such as font, rotation, and color can be specified here.
                    'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                    'rotation': 0,
                    'color': 7
                }
            )
            bot_length = round(cut_length_bottom * no_bars_bottom, 3) + round(cut_length_top * no_of_bars_top, 3)
            dia_string = str(round(bot_length * 6.321, 3))
            insert_point = (
                15.1 * cell_width,
                start_y - cell_height * 8.9)  # X, Y coordinates where the text will be inserted.
            text_height = 1
            # Add text to the modelspace.
            msp.add_text(
                dia_string,
                dxfattribs={
                    'insert': insert_point,
                    'height': text_height,
                    # Additional attributes such as font, rotation, and color can be specified here.
                    'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                    'rotation': 0,
                    'color': 7
                }
            )
        if (top_bar == 40 and main_bar == 40):
            bot_length = round(cut_length_bottom * no_bars_bottom, 3) + round(cut_length_top * no_of_bars_top, 3)
            dia_string = str(round(bot_length,3))
            insert_point = (
                16.1 * cell_width,
                start_y - cell_height * 6.9)  # X, Y coordinates where the text will be inserted.
            text_height = 1
            # Add text to the modelspace.
            msp.add_text(
                dia_string,
                dxfattribs={
                    'insert': insert_point,
                    'height': text_height,
                    # Additional attributes such as font, rotation, and color can be specified here.
                    'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                    'rotation': 0,
                    'color': 7
                }
            )
            bot_length = round(cut_length_bottom * no_bars_bottom, 3) + round(cut_length_top * no_of_bars_top, 3)
            dia_string = str(round(bot_length * 9.877, 3))
            insert_point = (
                16.1 * cell_width,
                start_y - cell_height * 8.9)  # X, Y coordinates where the text will be inserted.
            text_height = 1
            # Add text to the modelspace.
            msp.add_text(
                dia_string,
                dxfattribs={
                    'insert': insert_point,
                    'height': text_height,
                    # Additional attributes such as font, rotation, and color can be specified here.
                    'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                    'rotation': 0,
                    'color': 7
                }
            )
        if (top_bar == 12 and main_bar != 12):
            bot_length = round(cut_length_top * no_of_bars_top, 3)
            dia_string = str(round(bot_length,3))
            insert_point = (
                11.1 * cell_width,
                start_y - cell_height * 6.9)  # X, Y coordinates where the text will be inserted.
            text_height = 1
            # Add text to the modelspace.
            msp.add_text(
                dia_string,
                dxfattribs={
                    'insert': insert_point,
                    'height': text_height,
                    # Additional attributes such as font, rotation, and color can be specified here.
                    'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                    'rotation': 0,
                    'color': 7
                }
            )
            bot_length = round(cut_length_top * no_of_bars_top, 3)
            dia_string = str(round(bot_length * .889, 3))
            insert_point = (
                11.1 * cell_width,
                start_y - cell_height * 8.9)  # X, Y coordinates where the text will be inserted.
            text_height = 1
            # Add text to the modelspace.
            msp.add_text(
                dia_string,
                dxfattribs={
                    'insert': insert_point,
                    'height': text_height,
                    # Additional attributes such as font, rotation, and color can be specified here.
                    'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                    'rotation': 0,
                    'color': 7
                }
            )
        if (top_bar == 16 and main_bar != 16):
            bot_length = round(cut_length_top * no_of_bars_top, 3)
            dia_string = str(round(bot_length,3))
            insert_point = (
                12.1 * cell_width,
                start_y - cell_height * 6.9)  # X, Y coordinates where the text will be inserted.
            text_height = 1
            # Add text to the modelspace.
            msp.add_text(
                dia_string,
                dxfattribs={
                    'insert': insert_point,
                    'height': text_height,
                    # Additional attributes such as font, rotation, and color can be specified here.
                    'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                    'rotation': 0,
                    'color': 7
                }
            )
            bot_length = round(cut_length_top * no_of_bars_top, 3)
            dia_string = str(round(bot_length * 1.58, 3))
            insert_point = (
                12.1 * cell_width,
                start_y - cell_height * 8.9)  # X, Y coordinates where the text will be inserted.
            text_height = 1
            # Add text to the modelspace.
            msp.add_text(
                dia_string,
                dxfattribs={
                    'insert': insert_point,
                    'height': text_height,
                    # Additional attributes such as font, rotation, and color can be specified here.
                    'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                    'rotation': 0,
                    'color': 7
                }
            )
        if (top_bar == 20 and main_bar != 20):
            bot_length = round(cut_length_top * no_of_bars_top, 3)
            dia_string = str(round(bot_length,3))
            insert_point = (
                13.1 * cell_width,
                start_y - cell_height * 6.9)  # X, Y coordinates where the text will be inserted.
            text_height = 1
            # Add text to the modelspace.
            msp.add_text(
                dia_string,
                dxfattribs={
                    'insert': insert_point,
                    'height': text_height,
                    # Additional attributes such as font, rotation, and color can be specified here.
                    'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                    'rotation': 0,
                    'color': 7
                }
            )
            bot_length = round(cut_length_top * no_of_bars_top, 3)
            dia_string = str(round(bot_length * 2.469, 3))
            insert_point = (
                13.1 * cell_width,
                start_y - cell_height * 8.9)  # X, Y coordinates where the text will be inserted.
            text_height = 1
            # Add text to the modelspace.
            msp.add_text(
                dia_string,
                dxfattribs={
                    'insert': insert_point,
                    'height': text_height,
                    # Additional attributes such as font, rotation, and color can be specified here.
                    'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                    'rotation': 0,
                    'color': 7
                }
            )
        if (top_bar == 25 and main_bar != 25):
            bot_length = round(cut_length_top * no_of_bars_top, 3)
            dia_string = str(round(bot_length,3))
            insert_point = (
                14.1 * cell_width,
                start_y - cell_height * 6.9)  # X, Y coordinates where the text will be inserted.
            text_height = 1
            # Add text to the modelspace.
            msp.add_text(
                dia_string,
                dxfattribs={
                    'insert': insert_point,
                    'height': text_height,
                    # Additional attributes such as font, rotation, and color can be specified here.
                    'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                    'rotation': 0,
                    'color': 7
                }
            )
            bot_length = round(cut_length_top * no_of_bars_top, 3)
            dia_string = str(round(bot_length * 3.858, 3))
            insert_point = (
                14.1 * cell_width,
                start_y - cell_height * 8.9)  # X, Y coordinates where the text will be inserted.
            text_height = 1
            # Add text to the modelspace.
            msp.add_text(
                dia_string,
                dxfattribs={
                    'insert': insert_point,
                    'height': text_height,
                    # Additional attributes such as font, rotation, and color can be specified here.
                    'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                    'rotation': 0,
                    'color': 7
                }
            )
        if (top_bar == 32 and main_bar != 32):
            bot_length = round(cut_length_top * no_of_bars_top, 3)
            dia_string = str(round(bot_length,3))
            insert_point = (
                15.1 * cell_width,
                start_y - cell_height * 6.9)  # X, Y coordinates where the text will be inserted.
            text_height = 1
            # Add text to the modelspace.
            msp.add_text(
                dia_string,
                dxfattribs={
                    'insert': insert_point,
                    'height': text_height,
                    # Additional attributes such as font, rotation, and color can be specified here.
                    'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                    'rotation': 0,
                    'color': 7
                }
            )
            bot_length = round(cut_length_top * no_of_bars_top, 3)
            dia_string = str(round(bot_length * 6.321, 3))
            insert_point = (
                15.1 * cell_width,
                start_y - cell_height * 6.9)  # X, Y coordinates where the text will be inserted.
            text_height = 1
            # Add text to the modelspace.
            msp.add_text(
                dia_string,
                dxfattribs={
                    'insert': insert_point,
                    'height': text_height,
                    # Additional attributes such as font, rotation, and color can be specified here.
                    'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                    'rotation': 0,
                    'color': 7
                }
            )
        if (top_bar == 40 and main_bar != 40):
            bot_length = round(cut_length_top * no_of_bars_top, 3)
            dia_string = str(round(bot_length,3))
            insert_point = (
                16.1 * cell_width,
                start_y - cell_height * 6.9)  # X, Y coordinates where the text will be inserted.
            text_height = 1
            # Add text to the modelspace.
            msp.add_text(
                dia_string,
                dxfattribs={
                    'insert': insert_point,
                    'height': text_height,
                    # Additional attributes such as font, rotation, and color can be specified here.
                    'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                    'rotation': 0,
                    'color': 7
                }
            )
            bot_length = round(cut_length_top * no_of_bars_top, 3)
            dia_string = str(round(bot_length * 9.877, 3))
            insert_point = (
                16.1 * cell_width,
                start_y - cell_height * 8.9)  # X, Y coordinates where the text will be inserted.
            text_height = 1
            # Add text to the modelspace.
            msp.add_text(
                dia_string,
                dxfattribs={
                    'insert': insert_point,
                    'height': text_height,
                    # Additional attributes such as font, rotation, and color can be specified here.
                    'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                    'rotation': 0,
                    'color': 7
                }
            )
        if (top_bar != 12 and main_bar == 12):
            bot_length = round(cut_length_bottom * no_bars_bottom, 3)
            dia_string = str(bot_length)
            insert_point = (
                11.1 * cell_width,
                start_y - cell_height * 6.9)  # X, Y coordinates where the text will be inserted.
            text_height = 1
            # Add text to the modelspace.
            msp.add_text(
                dia_string,
                dxfattribs={
                    'insert': insert_point,
                    'height': text_height,
                    # Additional attributes such as font, rotation, and color can be specified here.
                    'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                    'rotation': 0,
                    'color': 7
                }
            )
            bot_length = round(cut_length_bottom * no_bars_bottom, 3)
            dia_string = str(round(bot_length * .889, 3))
            insert_point = (
                11.1 * cell_width,
                start_y - cell_height * 8.9)  # X, Y coordinates where the text will be inserted.
            text_height = 1
            # Add text to the modelspace.
            msp.add_text(
                dia_string,
                dxfattribs={
                    'insert': insert_point,
                    'height': text_height,
                    # Additional attributes such as font, rotation, and color can be specified here.
                    'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                    'rotation': 0,
                    'color': 7
                }
            )
        if (top_bar != 16 and main_bar == 16):
            bot_length = round(cut_length_bottom * no_bars_bottom, 3)
            dia_string = str(bot_length)
            insert_point = (
                12.1 * cell_width,
                start_y - cell_height * 6.9)  # X, Y coordinates where the text will be inserted.
            text_height = 1
            # Add text to the modelspace.
            msp.add_text(
                dia_string,
                dxfattribs={
                    'insert': insert_point,
                    'height': text_height,
                    # Additional attributes such as font, rotation, and color can be specified here.
                    'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                    'rotation': 0,
                    'color': 7
                }
            )
            bot_length = round(cut_length_bottom * no_bars_bottom, 3)
            dia_string = str(round(bot_length * 1.58, 3))
            insert_point = (
                12.1 * cell_width,
                start_y - cell_height * 8.9)  # X, Y coordinates where the text will be inserted.
            text_height = 1
            # Add text to the modelspace.
            msp.add_text(
                dia_string,
                dxfattribs={
                    'insert': insert_point,
                    'height': text_height,
                    # Additional attributes such as font, rotation, and color can be specified here.
                    'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                    'rotation': 0,
                    'color': 7
                }
            )
        if (top_bar != 20 and main_bar == 20):
            bot_length = round(cut_length_bottom * no_bars_bottom, 3)
            dia_string = str(bot_length)
            insert_point = (
                13.1 * cell_width,
                start_y - cell_height * 6.9)  # X, Y coordinates where the text will be inserted.
            text_height = 1
            # Add text to the modelspace.
            msp.add_text(
                dia_string,
                dxfattribs={
                    'insert': insert_point,
                    'height': text_height,
                    # Additional attributes such as font, rotation, and color can be specified here.
                    'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                    'rotation': 0,
                    'color': 7
                }
            )
            bot_length = round(cut_length_bottom * no_bars_bottom, 3)
            dia_string = str(round(bot_length * 2.469, 3))
            insert_point = (
                13.1 * cell_width,
                start_y - cell_height * 8.9)  # X, Y coordinates where the text will be inserted.
            text_height = 1
            # Add text to the modelspace.
            msp.add_text(
                dia_string,
                dxfattribs={
                    'insert': insert_point,
                    'height': text_height,
                    # Additional attributes such as font, rotation, and color can be specified here.
                    'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                    'rotation': 0,
                    'color': 7
                }
            )
        if (top_bar != 25 and main_bar == 25):
            bot_length = round(cut_length_bottom * no_bars_bottom, 3)
            dia_string = str(bot_length)
            insert_point = (
                14.1 * cell_width,
                start_y - cell_height * 6.9)  # X, Y coordinates where the text will be inserted.
            text_height = 1
            # Add text to the modelspace.
            msp.add_text(
                dia_string,
                dxfattribs={
                    'insert': insert_point,
                    'height': text_height,
                    # Additional attributes such as font, rotation, and color can be specified here.
                    'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                    'rotation': 0,
                    'color': 7
                }
            )
            bot_length = round(cut_length_bottom * no_bars_bottom, 3)
            dia_string = str(round(bot_length * 3.858, 3))
            insert_point = (
                14.1 * cell_width,
                start_y - cell_height * 8.9)  # X, Y coordinates where the text will be inserted.
            text_height = 1
            # Add text to the modelspace.
            msp.add_text(
                dia_string,
                dxfattribs={
                    'insert': insert_point,
                    'height': text_height,
                    # Additional attributes such as font, rotation, and color can be specified here.
                    'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                    'rotation': 0,
                    'color': 7
                }
            )
        if (top_bar != 32 and main_bar == 32):
            bot_length = round(cut_length_bottom * no_bars_bottom, 3)
            dia_string = str(bot_length)
            insert_point = (
                15.1 * cell_width,
                start_y - cell_height * 6.9)  # X, Y coordinates where the text will be inserted.
            text_height = 1
            # Add text to the modelspace.
            msp.add_text(
                dia_string,
                dxfattribs={
                    'insert': insert_point,
                    'height': text_height,
                    # Additional attributes such as font, rotation, and color can be specified here.
                    'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                    'rotation': 0,
                    'color': 7
                }
            )
            bot_length = round(cut_length_bottom * no_bars_bottom, 3)
            dia_string = str(round(bot_length * 6.321, 3))
            insert_point = (
                15.1 * cell_width,
                start_y - cell_height * 8.9)  # X, Y coordinates where the text will be inserted.
            text_height = 1
            # Add text to the modelspace.
            msp.add_text(
                dia_string,
                dxfattribs={
                    'insert': insert_point,
                    'height': text_height,
                    # Additional attributes such as font, rotation, and color can be specified here.
                    'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                    'rotation': 0,
                    'color': 7
                }
            )
        if (top_bar != 40 and main_bar == 40):
            bot_length = round(cut_length_bottom * no_bars_bottom, 3)
            dia_string = str(bot_length)
            insert_point = (
                16.1 * cell_width,
                start_y - cell_height * 6.9)  # X, Y coordinates where the text will be inserted.
            text_height = 1
            # Add text to the modelspace.
            msp.add_text(
                dia_string,
                dxfattribs={
                    'insert': insert_point,
                    'height': text_height,
                    # Additional attributes such as font, rotation, and color can be specified here.
                    'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                    'rotation': 0,
                    'color': 7
                }
            )
            bot_length = round(cut_length_bottom * no_bars_bottom, 3)
            dia_string = str(round(bot_length * 9.877, 3))
            insert_point = (
                16.1 * cell_width,
                start_y - cell_height * 8.9)  # X, Y coordinates where the text will be inserted.
            text_height = 1
            # Add text to the modelspace.
            msp.add_text(
                dia_string,
                dxfattribs={
                    'insert': insert_point,
                    'height': text_height,
                    # Additional attributes such as font, rotation, and color can be specified here.
                    'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                    'rotation': 0,
                    'color': 7
                }
            )

        msp.add_line((6 * cell_width, start_y - 6 * cell_height), (17 * cell_width, start_y - 6 * cell_height))

        # weigth calculation end-----------------------------------------------------------------
        bot_string = "length of Bar (m)"
        insert_point = (
            12 * cell_width + .8, start_y + cell_height / 2)  # X, Y coordinates where the text will be inserted.
        text_height = 1
        # Add text to the modelspace.
        msp.add_text(
            bot_string,
            dxfattribs={
                'insert': insert_point,
                'height': text_height,
                # Additional attributes such as font, rotation, and color can be specified here.
                'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                'rotation': 0,
                'color': 7
            }
        )
        dia_string = round(10 * 10 / 162, 3)
        insert_point = (
            10.1 * cell_width,
            start_y - cell_height * 7.9)  # X, Y coordinates where the text will be inserted.
        text_height = 1
        # Add text to the modelspace.
        msp.add_text(
            dia_string,
            dxfattribs={
                'insert': insert_point,
                'height': text_height,
                # Additional attributes such as font, rotation, and color can be specified here.
                'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                'rotation': 0,
                'color': 7
            }
        )
        dia_string = round(12 * 12 / 162, 3)
        insert_point = (
            11.1 * cell_width,
            start_y - cell_height * 7.9)  # X, Y coordinates where the text will be inserted.
        text_height = 1
        # Add text to the modelspace.
        msp.add_text(
            dia_string,
            dxfattribs={
                'insert': insert_point,
                'height': text_height,
                # Additional attributes such as font, rotation, and color can be specified here.
                'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                'rotation': 0,
                'color': 7
            }
        )
        dia_string = round(16 * 16 / 162, 3)
        insert_point = (
            12.1 * cell_width,
            start_y - cell_height * 7.9)  # X, Y coordinates where the text will be inserted.
        text_height = 1
        # Add text to the modelspace.
        msp.add_text(
            dia_string,
            dxfattribs={
                'insert': insert_point,
                'height': text_height,
                # Additional attributes such as font, rotation, and color can be specified here.
                'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                'rotation': 0,
                'color': 7
            }
        )
        dia_string = round(20 * 20 / 162, 3)
        insert_point = (
            13.1 * cell_width,
            start_y - cell_height * 7.9)  # X, Y coordinates where the text will be inserted.
        text_height = 1
        # Add text to the modelspace.
        msp.add_text(
            dia_string,
            dxfattribs={
                'insert': insert_point,
                'height': text_height,
                # Additional attributes such as font, rotation, and color can be specified here.
                'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                'rotation': 0,
                'color': 7
            }
        )
        dia_string = round(25 * 25 / 162, 3)
        insert_point = (
            14.1 * cell_width,
            start_y - cell_height * 7.9)  # X, Y coordinates where the text will be inserted.
        text_height = 1
        # Add text to the modelspace.
        msp.add_text(
            dia_string,
            dxfattribs={
                'insert': insert_point,
                'height': text_height,
                # Additional attributes such as font, rotation, and color can be specified here.
                'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                'rotation': 0,
                'color': 7
            }
        )
        dia_string = round(32 * 32 / 162, 3)
        insert_point = (
            15.1 * cell_width,
            start_y - cell_height * 7.9)  # X, Y coordinates where the text will be inserted.
        text_height = 1
        # Add text to the modelspace.
        msp.add_text(
            dia_string,
            dxfattribs={
                'insert': insert_point,
                'height': text_height,
                # Additional attributes such as font, rotation, and color can be specified here.
                'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                'rotation': 0,
                'color': 7
            }
        )
        dia_string = round(40 * 40 / 162, 3)
        insert_point = (
            16.1 * cell_width,
            start_y - cell_height * 7.9)  # X, Y coordinates where the text will be inserted.
        text_height = 1
        # Add text to the modelspace.
        msp.add_text(
            dia_string,
            dxfattribs={
                'insert': insert_point,
                'height': text_height,
                # Additional attributes such as font, rotation, and color can be specified here.
                'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                'rotation': 0,
                'color': 7
            }
        )
        if (stdia == 8):
            st_length = round(stirrup_cut_length * no_str, 3)
            dia_string = str(st_length)
            insert_point = (
                9.1 * cell_width,
                start_y - cell_height * 4.9)  # X, Y coordinates where the text will be inserted.
            text_height = 1
            # Add text to the modelspace.
            msp.add_text(
                dia_string,
                dxfattribs={
                    'insert': insert_point,
                    'height': text_height,
                    # Additional attributes such as font, rotation, and color can be specified here.
                    'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                    'rotation': 0,
                    'color': 7
                }
            )
            dia_string = round(8 * 8 / 162, 3)
            insert_point = (
                9.1 * cell_width,
                start_y - cell_height * 7.9)  # X, Y coordinates where the text will be inserted.
            text_height = 1
            # Add text to the modelspace.
            msp.add_text(
                dia_string,
                dxfattribs={
                    'insert': insert_point,
                    'height': text_height,
                    # Additional attributes such as font, rotation, and color can be specified here.
                    'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                    'rotation': 0,
                    'color': 7
                }
            )
            dia_string = round(8 * 8 / 162 * st_length, 3)
            insert_point = (
                9.1 * cell_width,
                start_y - cell_height * 8.9)  # X, Y coordinates where the text will be inserted.
            text_height = 1
            # Add text to the modelspace.
            msp.add_text(
                dia_string,
                dxfattribs={
                    'insert': insert_point,
                    'height': text_height,
                    # Additional attributes such as font, rotation, and color can be specified here.
                    'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                    'rotation': 0,
                    'color': 7
                }
            )
        if (main_bar == 12):
            bot_length = round(cut_length_bottom * no_bars_bottom, 3)
            dia_string = str(bot_length)
            insert_point = (
                11 * cell_width + .8,
                start_y - cell_height * 4 + .5)  # X, Y coordinates where the text will be inserted.
            text_height = 1
            # Add text to the modelspace.
            msp.add_text(
                dia_string,
                dxfattribs={
                    'insert': insert_point,
                    'height': text_height,
                    # Additional attributes such as font, rotation, and color can be specified here.
                    'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                    'rotation': 0,
                    'color': 7
                }
            )

        elif (main_bar == 16):
            bot_length = round(cut_length_bottom * no_bars_bottom, 3)
            dia_string = str(bot_length)
            insert_point = (
                12.1 * cell_width,
                start_y - cell_height * 3.9)  # X, Y coordinates where the text will be inserted.
            text_height = 1
            # Add text to the modelspace.
            msp.add_text(
                dia_string,
                dxfattribs={
                    'insert': insert_point,
                    'height': text_height,
                    # Additional attributes such as font, rotation, and color can be specified here.
                    'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                    'rotation': 0,
                    'color': 7
                }
            )

        elif (main_bar == 20):
            bot_length = round(cut_length_bottom * no_bars_bottom, 3)
            dia_string = str(bot_length)
            insert_point = (
                13.1 * cell_width,
                start_y - cell_height * 3.9)  # X, Y coordinates where the text will be inserted.
            text_height = 1
            # Add text to the modelspace.
            msp.add_text(
                dia_string,
                dxfattribs={
                    'insert': insert_point,
                    'height': text_height,
                    # Additional attributes such as font, rotation, and color can be specified here.
                    'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                    'rotation': 0,
                    'color': 7
                }
            )

        elif (main_bar == 25):
            bot_length = round(cut_length_bottom * no_bars_bottom, 3)
            dia_string = str(bot_length)
            insert_point = (
                14.1 * cell_width,
                start_y - cell_height * 3.9)  # X, Y coordinates where the text will be inserted.
            text_height = 1
            # Add text to the modelspace.
            msp.add_text(
                dia_string,
                dxfattribs={
                    'insert': insert_point,
                    'height': text_height,
                    # Additional attributes such as font, rotation, and color can be specified here.
                    'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                    'rotation': 0,
                    'color': 7
                }
            )

        elif (main_bar == 32):
            bot_length = round(cut_length_bottom * no_bars_bottom, 3)
            dia_string = str(bot_length)
            insert_point = (
                15.1 * cell_width,
                start_y - cell_height * 3.9)  # X, Y coordinates where the text will be inserted.
            text_height = 1
            # Add text to the modelspace.
            msp.add_text(
                dia_string,
                dxfattribs={
                    'insert': insert_point,
                    'height': text_height,
                    # Additional attributes such as font, rotation, and color can be specified here.
                    'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                    'rotation': 0,
                    'color': 7
                }
            )

        elif (main_bar == 40):
            bot_length = round(cut_length_bottom * no_bars_bottom, 3)
            dia_string = str(bot_length)
            insert_point = (
                16.1 * cell_width,
                start_y - cell_height * 3.9)  # X, Y coordinates where the text will be inserted.
            text_height = 1
            # Add text to the modelspace.
            msp.add_text(
                dia_string,
                dxfattribs={
                    'insert': insert_point,
                    'height': text_height,
                    # Additional attributes such as font, rotation, and color can be specified here.
                    'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                    'rotation': 0,
                    'color': 7
                }
            )

        # -----------------------------------------------------------------------------top dia total length
        if (top_bar == 12):
            top_length = round(cut_length_top * no_of_bars_top, 3)
            dia_string = str(top_length)
            insert_point = (
                11.1 * cell_width,
                start_y - cell_height * 2.9)  # X, Y coordinates where the text will be inserted.
            text_height = 1
            # Add text to the modelspace.
            msp.add_text(
                dia_string,
                dxfattribs={
                    'insert': insert_point,
                    'height': text_height,
                    # Additional attributes such as font, rotation, and color can be specified here.
                    'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                    'rotation': 0,
                    'color': 7
                }
            )
        elif (top_bar == 16):
            top_length = round(cut_length_top * no_of_bars_top, 3)
            dia_string = str(top_length)
            insert_point = (
                12 * cell_width + .8,
                start_y - cell_height * 3 + .5)  # X, Y coordinates where the text will be inserted.
            text_height = 1
            # Add text to the modelspace.
            msp.add_text(
                dia_string,
                dxfattribs={
                    'insert': insert_point,
                    'height': text_height,
                    # Additional attributes such as font, rotation, and color can be specified here.
                    'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                    'rotation': 0,
                    'color': 7
                }
            )

        elif (top_bar == 20):
            top_length = round(cut_length_top * no_of_bars_top, 3)
            dia_string = str(top_length)
            insert_point = (
            13 * cell_width + .8, start_y - cell_height * 3 + .5)  # X, Y coordinates where the text will be inserted.
            text_height = 1
            # Add text to the modelspace.
            msp.add_text(
                dia_string,
                dxfattribs={
                    'insert': insert_point,
                    'height': text_height,
                    # Additional attributes such as font, rotation, and color can be specified here.
                    'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                    'rotation': 0,
                    'color': 7
                }
            )
        elif (top_bar == 25):
            top_length = round(cut_length_top * no_of_bars_top, 3)
            dia_string = str(top_length)
            insert_point = (
            14 * cell_width + .8, start_y - cell_height * 3 + .5)  # X, Y coordinates where the text will be inserted.
            text_height = 1
            # Add text to the modelspace.
            msp.add_text(
                dia_string,
                dxfattribs={
                    'insert': insert_point,
                    'height': text_height,
                    # Additional attributes such as font, rotation, and color can be specified here.
                    'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                    'rotation': 0,
                    'color': 7
                }
            )
        elif (top_bar == 32):
            top_length = round(cut_length_top * no_of_bars_top, 3)
            dia_string = str(top_length)
            insert_point = (
            15 * cell_width + .8, start_y - cell_height * 3 + .5)  # X, Y coordinates where the text will be inserted.
            text_height = 1
            # Add text to the modelspace.
            msp.add_text(
                dia_string,
                dxfattribs={
                    'insert': insert_point,
                    'height': text_height,
                    # Additional attributes such as font, rotation, and color can be specified here.
                    'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                    'rotation': 0,
                    'color': 7
                }
            )
        elif (top_bar == 40):
            top_length = round(cut_length_top * no_of_bars_top, 3)
            dia_string = str(top_length)
            insert_point = (
            16 * cell_width + .8, start_y - cell_height * 3 + .5)  # X, Y coordinates where the text will be inserted.
            text_height = 1
            # Add text to the modelspace.
            msp.add_text(
                dia_string,
                dxfattribs={
                    'insert': insert_point,
                    'height': text_height,
                    # Additional attributes such as font, rotation, and color can be specified here.
                    'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                    'rotation': 0,
                    'color': 7
                }
            )
        # side face reinforcement -------------------------------------------------------------------------------------------
        if (o_d >= 750):
            msp.add_line((1.3 * cell_width, start_y - cell_height * 5.5),
                         (1.8 * cell_width, start_y - cell_height * 5.5))
            dia_string = "Side Face "
            insert_point = (
                .1 * cell_width, start_y - cell_height * 5.5)  # X, Y coordinates where the text will be inserted.
            text_height = .5
            # Add text to the modelspace.
            msp.add_text(
                dia_string,
                dxfattribs={
                    'insert': insert_point,
                    'height': text_height,
                    # Additional attributes such as font, rotation, and color can be specified here.
                    'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                    'rotation': 0,
                    'color': 7
                }
            )
            bar_string = "Nil"
            insert_point = (
                4.5 * cell_width, start_y - cell_height * 5.5)  # X, Y coordinates where the text will be inserted.
            text_height = .5
            # Add text to the modelspace.
            msp.add_text(
                bar_string,
                dxfattribs={
                    'insert': insert_point,
                    'height': text_height,
                    # Additional attributes such as font, rotation, and color can be specified here.
                    'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                    'rotation': 0,
                    'color': 7
                }
            )
            bar_string = "Nil"
            insert_point = (
                2.5 * cell_width, start_y - cell_height * 5.5)  # X, Y coordinates where the text will be inserted.
            text_height = .5
            # Add text to the modelspace.
            msp.add_text(
                bar_string,
                dxfattribs={
                    'insert': insert_point,
                    'height': text_height,
                    # Additional attributes such as font, rotation, and color can be specified here.
                    'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                    'rotation': 0,
                    'color': 7
                }
            )
            bar_string = "Nil"
            insert_point = (
                6.5 * cell_width, start_y - cell_height * 5.5)  # X, Y coordinates where the text will be inserted.
            text_height = .5
            # Add text to the modelspace.
            msp.add_text(
                bar_string,
                dxfattribs={
                    'insert': insert_point,
                    'height': text_height,
                    # Additional attributes such as font, rotation, and color can be specified here.
                    'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                    'rotation': 0,
                    'color': 7
                }
            )
            dia_string = "b"
            insert_point = (
                1.45 * cell_width, start_y - cell_height * 5.4)  # X, Y coordinates where the text will be inserted.
            text_height = .5
            # Add text to the modelspace.
            msp.add_text(
                dia_string,
                dxfattribs={
                    'insert': insert_point,
                    'height': text_height,
                    # Additional attributes such as font, rotation, and color can be specified here.
                    'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                    'rotation': 0,
                    'color': 7
                }
            )
            side_length = clear_span * 100000 - 200 * nominal_cover + wall_thickness * 200
            dia_string = str(side_length / 1000)
            insert_point = (
                3.45 * cell_width, start_y - cell_height * 5.4)  # X, Y coordinates where the text will be inserted.
            text_height = .5
            # Add text to the modelspace.
            msp.add_text(
                dia_string,
                dxfattribs={
                    'insert': insert_point,
                    'height': text_height,
                    # Additional attributes such as font, rotation, and color can be specified here.
                    'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                    'rotation': 0,
                    'color': 7
                }
            )
            dia_string = str(no_of_bars_side * 2)
            insert_point = (
                8.1 * cell_width, start_y - cell_height * 5.9)  # X, Y coordinates where the text will be inserted.
            text_height = .8
            # Add text to the modelspace.
            msp.add_text(
                dia_string,
                dxfattribs={
                    'insert': insert_point,
                    'height': text_height,
                    # Additional attributes such as font, rotation, and color can be specified here.
                    'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                    'rotation': 0,
                    'color': 7
                }
            )
            dia_string = str(side_length / 1000)
            insert_point = (
                7.1 * cell_width, start_y - cell_height * 5.9)  # X, Y coordinates where the text will be inserted.
            text_height = .8
            # Add text to the modelspace.
            msp.add_text(
                dia_string,
                dxfattribs={
                    'insert': insert_point,
                    'height': text_height,
                    # Additional attributes such as font, rotation, and color can be specified here.
                    'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                    'rotation': 0,
                    'color': 7
                }
            )
            dia_string = str(side_bar)
            insert_point = (
                5.5 * cell_width, start_y - cell_height * 5.9)  # X, Y coordinates where the text will be inserted.
            text_height = .8
            # Add text to the modelspace.
            msp.add_text(
                dia_string,
                dxfattribs={
                    'insert': insert_point,
                    'height': text_height,
                    # Additional attributes such as font, rotation, and color can be specified here.
                    'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                    'rotation': 0,
                    'color': 7
                }
            )
            dia_string = " Side Face Weight Reinforcement  is Directly Added at the end to avoid confusion"
            insert_point = (
                17.1 * cell_width, start_y - cell_height * 8.9)  # X, Y coordinates where the text will be inserted.
            text_height = 1
            # Add text to the modelspace.
            msp.add_text(
                dia_string,
                dxfattribs={
                    'insert': insert_point,
                    'height': text_height,
                    # Additional attributes such as font, rotation, and color can be specified here.
                    'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                    'rotation': 0,
                    'color': 7
                }
            )
            if (side_bar == 12):
                dia_string = str(side_length * no_of_bars_side * 2 / 1000)
                insert_point = (
                    11.1 * cell_width, start_y - cell_height * 5.9)  # X, Y coordinates where the text will be inserted.
                text_height = .8
                # Add text to the modelspace.
                msp.add_text(
                    dia_string,
                    dxfattribs={
                        'insert': insert_point,
                        'height': text_height,
                        # Additional attributes such as font, rotation, and color can be specified here.
                        'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                        'rotation': 0,
                        'color': 7
                    }
                )

            if (side_bar == 16):
                dia_string = str(side_length * no_of_bars_side * 2 / 1000)
                insert_point = (
                    12.1 * cell_width, start_y - cell_height * 5.9)  # X, Y coordinates where the text will be inserted.
                text_height = .8
                # Add text to the modelspace.
                msp.add_text(
                    dia_string,
                    dxfattribs={
                        'insert': insert_point,
                        'height': text_height,
                        # Additional attributes such as font, rotation, and color can be specified here.
                        'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                        'rotation': 0,
                        'color': 7
                    }
                )

            if (side_bar == 20):
                dia_string = str(side_length * no_of_bars_side * 2 / 1000)
                insert_point = (
                    13.1 * cell_width, start_y - cell_height * 5.9)  # X, Y coordinates where the text will be inserted.
                text_height = .8
                # Add text to the modelspace.
                msp.add_text(
                    dia_string,
                    dxfattribs={
                        'insert': insert_point,
                        'height': text_height,
                        # Additional attributes such as font, rotation, and color can be specified here.
                        'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                        'rotation': 0,
                        'color': 7
                    }
                )
            if (side_bar == 25):
                dia_string = str(side_length * no_of_bars_side * 2 / 1000)
                insert_point = (
                    14.1 * cell_width, start_y - cell_height * 5.9)  # X, Y coordinates where the text will be inserted.
                text_height = .8
                # Add text to the modelspace.
                msp.add_text(
                    dia_string,
                    dxfattribs={
                        'insert': insert_point,
                        'height': text_height,
                        # Additional attributes such as font, rotation, and color can be specified here.
                        'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                        'rotation': 0,
                        'color': 7
                    }
                )
            if (side_bar == 32):
                dia_string = str(side_length * no_of_bars_side * 2 / 1000)
                insert_point = (
                    15.1 * cell_width, start_y - cell_height * 5.9)  # X, Y coordinates where the text will be inserted.
                text_height = .8
                # Add text to the modelspace.
                msp.add_text(
                    dia_string,
                    dxfattribs={
                        'insert': insert_point,
                        'height': text_height,
                        # Additional attributes such as font, rotation, and color can be specified here.
                        'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                        'rotation': 0,
                        'color': 7
                    }
                )
            if (side_bar == 40):
                dia_string = str(side_length * no_of_bars_side * 2 / 1000)
                insert_point = (
                    16.1 * cell_width, start_y - cell_height * 5.9)  # X, Y coordinates where the text will be inserted.
                text_height = .8
                # Add text to the modelspace.
                msp.add_text(
                    dia_string,
                    dxfattribs={
                        'insert': insert_point,
                        'height': text_height,
                        # Additional attributes such as font, rotation, and color can be specified here.
                        'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                        'rotation': 0,
                        'color': 7
                    }
                )
        if (o_d >= 750):
            if (side_bar == 12):
                side_l = round(side_length * no_of_bars_side * .889 * 2 / 1000, 3)
            elif (side_bar == 16):
                side_l = round(side_length * no_of_bars_side * 1.58 * 2 / 1000, 3)
            elif (side_bar == 20):
                side_l = round(side_length * no_of_bars_side * 2.469 * 2 / 1000, 3)
            elif (side_bar == 25):
                side_l = round(side_length * no_of_bars_side * 3.858 * 2 / 1000, 3)
            elif (side_bar == 32):
                side_l = round(side_length * no_of_bars_side * 6.321 * 2 / 1000, 3)
            elif (side_bar == 40):
                side_l = round(side_length * no_of_bars_side * 9.887 * 2 / 1000, 3)
        else:
            side_l = 0
        bot_length = round(cut_length_bottom * no_bars_bottom * main_bar * main_bar / 162, 3) + round(
            cut_length_top * no_of_bars_top * top_bar * top_bar / 162, 3) + round(
            stirrup_cut_length * no_str * stdia * stdia / 162, 3) + side_l
        dia_string = str(round(bot_length, 3))
        insert_point = (
            13.1 * cell_width,
            start_y - cell_height * 9.9)  # X, Y coordinates where the text will be inserted.
        text_height = 1
        # Add text to the modelspace.
        msp.add_text(
            dia_string,
            dxfattribs={
                'insert': insert_point,
                'height': text_height,
                # Additional attributes such as font, rotation, and color can be specified here.
                'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                'rotation': 0,
                'color': 7
            }
        )

        # cuuting m
        dia_string = "(m)"
        insert_point = (
            7.5 * cell_width,
            start_y - cell_height * 1.5)  # X, Y coordinates where the text will be inserted.
        text_height = .5
        # Add text to the modelspace.
        msp.add_text(
            dia_string,
            dxfattribs={
                'insert': insert_point,
                'height': text_height,
                # Additional attributes such as font, rotation, and color can be specified here.
                'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                'rotation': 0,
                'color': 7
            }
        )
        dia_string = "No's"
        insert_point = (
            8.5 * cell_width,
            start_y - cell_height * 1.5)  # X, Y coordinates where the text will be inserted.
        text_height = .5
        # Add text to the modelspace.
        msp.add_text(
            dia_string,
            dxfattribs={
                'insert': insert_point,
                'height': text_height,
                # Additional attributes such as font, rotation, and color can be specified here.
                'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                'rotation': 0,
                'color': 7
            }
        )
        # dia total length end------------------------------------------------------------------------------------------
        headers = [
            "Type", "Bar Shape", "a (m)", "b (m)", "c (m)",
            "Dia (mm)", "Spacing (mm)", "Cutting Length ", "no's", "8 (mm)", "10 (mm)", "12 (mm)", "16 (mm)", "20 (mm)",
            "25 (mm)", "32 (mm)", "40 (mm)"
        ]

        # Number of rows
        num_rows = 4
        total_columns = len(headers)

        # Create headers
        for i, header in enumerate(headers):
            x = start_x + i * cell_width
            msp.add_lwpolyline(
                [(x, start_y), (x + cell_width, start_y), (x + cell_width, start_y - header_height),
                 (x, start_y - header_height), (x, start_y)],
                close=True
            )


            msp.add_text(header, dxfattribs={'height': 0.75}).set_dxf_attrib('insert',
                                                                                (x + .5, start_y - header_height / 2))


        # Add length headers

        # Creating Rows
        for row in range(num_rows):
            for col in range(total_columns):
                x = start_x + col * cell_width
                y = start_y - header_height - (row + 1) * cell_height

                # Draw the cell
                msp.add_lwpolyline(
                    [(x, y), (x + cell_width, y), (x + cell_width, y + cell_height), (x, y + cell_height), (x, y)],
                    close=True
                )

                # Sample text filling (you can fill in actual data)
                if col == 0:
                    text = str(row + 1)  # Bar no.
                elif col == 1 and row == 0:  # First row, Bar Shape
                    # Example shape: U-shaped bar
                    shape_x = x + cell_width / 2
                    shape_y = y + cell_height / 2
                    msp.add_lwpolyline([(shape_x - 2, shape_y), (shape_x + 2, shape_y)],
                                       dxfattribs={'layer': '0'})  # Horizontal line
                    msp.add_lwpolyline([(shape_x - 2, shape_y), (shape_x - 2, shape_y + 1)],
                                       dxfattribs={'layer': '0'})  # Vertical line left
                    msp.add_lwpolyline([(shape_x + 2, shape_y), (shape_x + 2, shape_y + 1)],
                                       dxfattribs={'layer': '0'})  # Vertical line right
                    continue
                elif col < len(headers):  # Dummy text for other cells
                    text = f'R{row + 1}C{col + 1}'
                else:  # Dummy length values
                    text = str(round((row + 1) * (col + 1) / 10, 2))

        # --------------------------------------------------END BBS---------------------------------------------------------------
        #hook -text ------------------------------------
        text_content = f"Y-{stdia} Stirrup @ {max_spacing} mm c/c"
        text_location = (1000 * clear_span + nominal_cover + top_bar / 100,
                         -4.45 * overall_depth - nominal_cover)  # Positioning the text outside the rectangle
        dimstyle = msp.doc.dimstyles.get('EZDXF')  # Get the 'Standard' DIMSTYLE or create a new one
        dimstyle.dxf.dimasz = nominal_cover * 3
        msp.add_text(
            text_content,
            dxfattribs={
                'height': .2,  # Text height
                'layer': 'TEXT',  # Optional: specify a layer for the text
                'color': 7,
                # Optional: specify text color
                'insert': text_location,  # Position of the text
            }
        )
        leader_points = [
            (1000 * clear_span - wall_thickness + nominal_cover, -4.5 * overall_depth - nominal_cover),
            # Start inside the rectangle
            (1000 * clear_span - wall_thickness + wall_thickness / 2, -4.4 * overall_depth - nominal_cover),
            # First bend point
            (1000 * clear_span + nominal_cover + top_bar / 100, -4.4 * overall_depth - nominal_cover)
            # End point at the text location
        ]

        msp.add_leader(leader_points, dxfattribs={
            'color': 7,
            'dimstyle': 'EZDXF'})

        text_content = f"Y-{stdia} Stirrup @ {max_spacing} mm c/c"
        text_location = (500 * clear_span + nominal_cover + top_bar / 100,
                         -4.45 * overall_depth - nominal_cover)  # Positioning the text outside the rectangle
        dimstyle = msp.doc.dimstyles.get('EZDXF')  # Get the 'Standard' DIMSTYLE or create a new one
        dimstyle.dxf.dimasz = nominal_cover * 3
        msp.add_text(
            text_content,
            dxfattribs={
                'height': .2,  # Text height
                'layer': 'TEXT',  # Optional: specify a layer for the text
                'color': 7,
                # Optional: specify text color
                'insert': text_location,  # Position of the text
            }
        )
        leader_points = [
            (500 * clear_span - wall_thickness + nominal_cover, -4.5 * overall_depth - nominal_cover),
            # Start inside the rectangle
            (500 * clear_span - wall_thickness + wall_thickness / 2, -4.4 * overall_depth - nominal_cover),
            # First bend point
            (500 * clear_span + nominal_cover + top_bar / 100, -4.4 * overall_depth - nominal_cover)
            # End point at the text location
        ]

        msp.add_leader(leader_points, dxfattribs={
            'color': 7,
            'dimstyle': 'EZDXF'})

        text_content = f"Y-{stdia} Stirrup @ {max_spacing} mm c/c"
        text_location = (wall_thickness + nominal_cover + top_bar / 100,
                         -4.45 * overall_depth - nominal_cover)  # Positioning the text outside the rectangle
        dimstyle = msp.doc.dimstyles.get('EZDXF')  # Get the 'Standard' DIMSTYLE or create a new one
        dimstyle.dxf.dimasz = nominal_cover * 3
        msp.add_text(
            text_content,
            dxfattribs={
                'height': .2,  # Text height
                'layer': 'TEXT',  # Optional: specify a layer for the text
                'color': 7,
                # Optional: specify text color
                'insert': text_location,  # Position of the text
            }
        )
        leader_points = [
            (+ nominal_cover, -4.5 * overall_depth - nominal_cover),
            # Start inside the rectangle
            (wall_thickness / 2, -4.4 * overall_depth - nominal_cover),
            # First bend point
            (wall_thickness + top_bar / 100, -4.4 * overall_depth - nominal_cover)
            # End point at the text location
        ]

        msp.add_leader(leader_points, dxfattribs={
            'color': 7,
            'dimstyle': 'EZDXF'})

        # detailing text----------------------------------------------------------------------------
        text_string = f"6. Top Reinforcemnet :- Provide {no_of_bars_top} no's of {top_bar} mm throughout the top and {no_of_bars_bottom//2} no's of {main_bar} mm curtail at L/3 from the face of the support"
        insert_point = (20 + 1000 * clear_span, 1)  # X, Y coordinates where the text will be inserted.
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
        text_string = f"5. Bottom Reinforcemnet :- Provide {no_of_bars_top} no's of {main_bar} mm throughout the Bottom and {no_of_bars_bottom//2} no's of {main_bar} mm curtail at L/3 from the face of the support"
        insert_point = (20 + 1000 * clear_span, 3)  # X, Y coordinates where the text will be inserted.
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
        text_string = f"4. Shear Reinforcemnet :- Provide {stdia} mm as vertical stirrups @ {max_spacing} mm c/c "
        insert_point = (20 + 1000 * clear_span, 5)  # X, Y coordinates where the text will be inserted.
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
        ml = round(ml, 3)
        mu = round(mu, 3)
        sf = round(ultimate_shear_force, 3)
        text_string = f"3. Mulimt :- {ml} KNm , Ultimate Bending Moment :- {mu} kNm ,Ultimate Shear Force :- {sf} kN"
        insert_point = (20 + 1000 * clear_span, 7)  # X, Y coordinates where the text will be inserted.
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
        text_string = f"2. Concrete Grade :- {fck} MPa , Steel Grade :- fe{fy}  "
        insert_point = (20 + 1000 * clear_span, 9)  # X, Y coordinates where the text will be inserted.
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
        text_string = f"1. Nominal Cover :- {nominal_cover * 100} mm  "
        insert_point = (20 + 1000 * clear_span, 11)  # X, Y coordinates where the text will be inserted.
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
        text_string = f"Notes :- "
        insert_point = (10 + 1000 * clear_span, 15)  # X, Y coordinates where the text will be inserted.
        text_height = 2  # Height of the text.

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
        text_string = f"7. Ductlie Reinforcement is Provided with minimum consideration"
        insert_point = (20 + 1000 * clear_span, -1)  # X, Y coordinates where the text will be inserted.
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
        if(o_d>=750):
            text_string = f"7. Side Face Reinforcement :- Provide {no_of_bars_side} No's of {side_bar}mm on each Face  "
            insert_point = (20 + 1000 * clear_span, -3)  # X, Y coordinates where the text will be inserted.
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
        start_point = (10 + 1000 * clear_span, 13)
        end_point = (140 + 1000 * clear_span, 13)

        msp.add_line(start_point, end_point, dxfattribs={
            'color': 7,  # Optional: specify the color
            'linetype': 'DASHED'  # Apply the hidden linetype
        })
        start_point = (10 + 1000 * clear_span, 13)
        end_point = (10 + 1000 * clear_span, -5)

        msp.add_line(start_point, end_point, dxfattribs={
            'color': 7,  # Optional: specify the color
            'linetype': 'DASHED'  # Apply the hidden linetype
        })
        start_point = (140 + 1000 * clear_span, 13)
        end_point = (140 + 1000 * clear_span, -5)

        msp.add_line(start_point, end_point, dxfattribs={
            'color': 7,  # Optional: specify the color
            'linetype': 'DASHED'  # Apply the hidden linetype
        })
        start_point = (10 + 1000 * clear_span, -5)
        end_point = (140 + 1000 * clear_span, -5)

        msp.add_line(start_point, end_point, dxfattribs={
            'color': 7,  # Optional: specify the color
            'linetype': 'DASHED'  # Apply the hidden linetype
        })

        #ast details
        a = round(ast, 3)
        txt_content = f"Ast Required in Tension Region :- {a} mm2"
        insert_point = (
            20 + 1000 * clear_span, 40)  # X, Y coordinates where the text will be inserted.
        text_height = .8
        # Add text to the modelspace.
        msp.add_text(
            txt_content,
            dxfattribs={
                'insert': insert_point,
                'height': text_height,
                # Additional attributes such as font, rotation, and color can be specified here.
                'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                'rotation': 0,
                'color': 7
            }
        )
        txt_content = f"Dia of Bar             No's         Ast Provided mm2                 Pt(%)"
        insert_point = (
            20 + 1000 * clear_span, 38)  # X, Y coordinates where the text will be inserted.
        text_height = .8
        # Add text to the modelspace.
        msp.add_text(
            txt_content,
            dxfattribs={
                'insert': insert_point,
                'height': text_height,
                # Additional attributes such as font, rotation, and color can be specified here.
                'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                'rotation': 0,
                'color': 7
            }
        )

        x12 = math.ceil(ast / 113.041)
        a12 = round(x12 * 113.041, 3)
        p12 = round(100 * a12 / (b * effective_depth), 3)
        txt_content = f"12 mm                {x12}               {a12}                     {p12}"
        insert_point = (
            20 + 1000 * clear_span, 36)  # X, Y coordinates where the text will be inserted.
        text_height = .8
        # Add text to the modelspace.
        msp.add_text(
            txt_content,
            dxfattribs={
                'insert': insert_point,
                'height': text_height,
                # Additional attributes such as font, rotation, and color can be specified here.
                'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                'rotation': 0,
                'color': 7
            }
        )
        x12 = math.ceil(ast / 200.961)
        a12 = round(x12 * 200.961, 3)
        p12 = round(100 * a12 / (b * effective_depth), 3)
        txt_content = f"16 mm                {x12}               {a12}                     {p12}"
        insert_point = (
            20 + 1000 * clear_span, 34)  # X, Y coordinates where the text will be inserted.
        text_height = .8
        # Add text to the modelspace.
        msp.add_text(
            txt_content,
            dxfattribs={
                'insert': insert_point,
                'height': text_height,
                # Additional attributes such as font, rotation, and color can be specified here.
                'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                'rotation': 0,
                'color': 7
            }
        )
        x12 = math.ceil(ast / 314.001)
        a12 = round(x12 * 314.001, 3)
        p12 = round(100 * a12 / (b * effective_depth), 3)
        txt_content = f"20 mm                {x12}               {a12}                     {p12}"
        insert_point = (
            20 + 1000 * clear_span, 32)  # X, Y coordinates where the text will be inserted.
        text_height = .8
        # Add text to the modelspace.
        msp.add_text(
            txt_content,
            dxfattribs={
                'insert': insert_point,
                'height': text_height,
                # Additional attributes such as font, rotation, and color can be specified here.
                'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                'rotation': 0,
                'color': 7
            }
        )
        x12 = math.ceil(ast / 490.625)
        a12 = round(x12 * 490.625, 3)
        p12 = round(100 * a12 / (b * effective_depth), 3)
        txt_content = f"25 mm                {x12}               {a12}                     {p12}"
        insert_point = (
            20 + 1000 * clear_span, 30)  # X, Y coordinates where the text will be inserted.
        text_height = .8
        # Add text to the modelspace.
        msp.add_text(
            txt_content,
            dxfattribs={
                'insert': insert_point,
                'height': text_height,
                # Additional attributes such as font, rotation, and color can be specified here.
                'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                'rotation': 0,
                'color': 7
            }
        )
        x12 = math.ceil(ast / 803.841)
        a12 = round(x12 * 803.841, 3)
        p12 = round(100 * a12 / (b * effective_depth), 3)
        txt_content = f"32 mm                {x12}               {a12}                     {p12}"
        insert_point = (
            20 + 1000 * clear_span, 28)  # X, Y coordinates where the text will be inserted.
        text_height = .8
        # Add text to the modelspace.
        msp.add_text(
            txt_content,
            dxfattribs={
                'insert': insert_point,
                'height': text_height,
                # Additional attributes such as font, rotation, and color can be specified here.
                'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                'rotation': 0,
                'color': 7
            }
        )
        x12 = math.ceil(ast / 1256.001)
        a12 = round(x12 * 1256.001, 3)
        p12 = round(100 * a12 / (b * effective_depth), 3)
        txt_content = f"40 mm                {x12}               {a12}                     {p12}"
        insert_point = (
            20 + 1000 * clear_span, 26)  # X, Y coordinates where the text will be inserted.
        text_height = .8
        # Add text to the modelspace.
        msp.add_text(
            txt_content,
            dxfattribs={
                'insert': insert_point,
                'height': text_height,
                # Additional attributes such as font, rotation, and color can be specified here.
                'style': 'OpenSans',  # Ensure the font style is available in your DXF viewer.
                'rotation': 0,
                'color': 7
            }
        )
        if (pt >= 4):
            return ("Tension Reinforcement Exceeds 4%")
            sys.exit()
        dis_bar=top_bar
        lef=clear_span*1000+wall_thickness
        tl=live_load+25*b*overall_depth
        span_d=15
        deff=effective_depth
        astreq=ast
        xorigin=clear_span
        width=clear_span
        ubm=ultimate_bending_moment
        sfm=ultimate_shear_force
        astshorprov = (main_bar * main_bar * 0.7857)*no_of_bars_top
        pst = (100 * astshorprov) / (1000 * effective_depth)
        astshorprov = ( dis_bar * dis_bar * 0.7857) *no_of_bars_top
        plt = (100 * astshorprov) / (1000 * effective_depth)
        texts = [
            f"                                   Design of Fixed Beam ",
            "Input Data:- - -  - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -",
            f"Effective Length                  ={lef*100:.2f} mm",
            f"Width of the support              ={wall_thickness*100} mm",
            f"Grade of Concrete                 ={fck} MPa",
            f"Grade of steel                    =fe{fy} ",
            f"Imposed Load                      ={ll} kN/m",
            f"Self Weight                       ={odt * 25*wtt/1000000:.2f} kN/m",
            f"Total Load                        ={ll+odt * 25*wtt/1000000:.2f} kN/m",
            "Dimensions:- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -  ",
            f"Span/d ratio                       ={spant:.2f}",
            f"Effective Cover                    ={overall_depth*100 - effective_depth} mm",
            f"Overall Depth                      ={overall_depth*100}mm",
            "Analysis of Slab- -  - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - ",
            f"Factor of Safety                   =1.5 ",
            f"Ultimate Bending Moment             ={mu :.2f} kNm/m",
            f"Ultimate shear force               ={ sf:.2f} kN/m",
            "Moment of Resistance of the Slab- -  - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -",
            "Short Span :-",
            f"Mux,l                                ={Ml / 10 ** 6:.2f} kNm/m",
            f"Depth of Neutral Axis                ={xumax * deff:.2f} mm",
            "Mux < Mux,l ,The section is singly reinforced ",
            "Area of Steel Tension (Bottom Bars)- -  - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - ",
            f"Ast:-                                  ={astreq:.2f} mm2 ",
            f"Ast,min                                ={astmin:.2f} mm2",
            f"Ast,max                                ={astmax} mm2",
            f"Ast Governing                          ={max(astreq, astmin):.2f} mm2",
            f"No of Bars                             = {no_of_bars_bottom} No's ",
            f"Dia of Bars                            = {main_bar} mm",
            f" Bottom Reinforcement :- Provide {no_of_bars_top} no's of {main_bar} mm throughout the Bottom and {no_of_bars_bottom//2} no's of {main_bar} mm curtail at L/3 from the face of the support",
            f"Ast,provided                           ={( main_bar * main_bar * 0.7857) *no_of_bars_top:.2f}",
            f"Percentage of steel                    ={pst:.3f} % "
            "Area of Steel Compression (Top Bars)- -  - - - - - - - - - - - - - - - - - - - - - - - ",
            f"Ast:-                                  ={astmin:.2f} mm2 ",
            f"Ast,min                                ={astmin:.2f} mm2",
            f"Ast,max                                ={astmax} mm2",
            f"Ast Governing                          ={max(astmin, astmin):.2f} mm2",
            f"No of Bars                             = {no_of_bars_top} No's",
            f"Dia of Bars                            = {top_bar} mm",
            f" Top Reinforcemnet :- Provide {no_of_bars_top} no's of {top_bar} mm throughout the top and {no_of_bars_bottom//2} no's of {main_bar} mm curtail at L/3 from the face of the support",
            f"Ast,provived                           ={( dis_bar * dis_bar * 0.7857) *no_of_bars_top:.2f}",
            f"Percentage of steel                    ={plt:.3f} % ",
            "Check for Shear- -  - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - ",
            f"Tv                                  ={tv:.2f} N/mm2 ",
            f"Tc                                  ={tc:.2f} mm2",
            f"Tv <  Tc ,Section is Safe under Shear Force",
            f" Shear Reinforcemnet :- Provide {stdia} mm as vertical stirrups @ {max_spacing} mm c/c "
            "Check for Deflection- -  - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -",
            f"fs                                ={fs:.2f} N/mm2 ",
            f"Modification factor                 ={mf:.2f}",
            f"span/d limit                        ={20 * mf:.2f}",
            f"Actual span/d                      ={lef *100/ effective_depth:.2f}",
            "Actual Span/d is greater than (span/d)limit , Hence Section is Safe under deflection"

            # Add more text as needed
        ]

        # Initial Y-coordinate
        y_location = width - overall_depth * 30

        # Loop through the text list
        for i, text_content in enumerate(texts):
            text_location = (
                xorigin + 6 * wall_thickness,  # X-coordinate remains constant
                y_location  # Y-coordinate decreases by overall_depth after each iteration
            )

            msp.add_text(
                text_content,
                dxfattribs={
                    'height': wall_thickness / 8,  # Text height
                    'layer': 'TEXT',  # Optional: specify a layer for the text
                    'color': 7,  # Optional: specify text color
                    'insert': text_location,  # X, Y coordinates
                }
            )

            # Decrease the Y-coordinate by overall_depth for the next text
            y_location -= overall_depth
        msp.add_line((xorigin + 5 * wall_thickness, width - overall_depth * 20),
                     (xorigin + 30 * wall_thickness, width - overall_depth * 20))
        msp.add_line((xorigin + 30 * wall_thickness, width - overall_depth * 20),
                     (xorigin + 30 * wall_thickness, y_location))
        msp.add_line((xorigin + 5 * wall_thickness, width - overall_depth * 20),
                     (xorigin + 5 * wall_thickness, y_location))
        msp.add_line((xorigin + 30 * wall_thickness, y_location),
                     (xorigin + 5 * wall_thickness, y_location))

        # project name
        msp.add_line((xorigin + 5 * wall_thickness, width - overall_depth * 25),
                     (xorigin + 30 * wall_thickness, width - overall_depth * 25))
        msp.add_line((xorigin + 5 * wall_thickness, width - overall_depth * 28),
                     (xorigin + 30 * wall_thickness, width - overall_depth * 28))
        msp.add_line((xorigin + 15 * wall_thickness, width - overall_depth * 22),
                     (xorigin + 30 * wall_thickness, width - overall_depth * 22))
        msp.add_line((xorigin + 10 * wall_thickness, width - overall_depth * 20),
                     (xorigin + 10 * wall_thickness, width - overall_depth * 28))
        msp.add_line((xorigin + 15 * wall_thickness, width - overall_depth * 20),
                     (xorigin + 15 * wall_thickness, width - overall_depth * 28))
        text_content = "Project :"
        text_location = (6 * wall_thickness + xorigin, width - 22.5 * overall_depth)

        msp.add_text(
            text_content,
            dxfattribs={
                'height': wall_thickness / 4,  # Text height
                'layer': 'TEXT',  # Optional: specify a layer for the text
                'color': 10,  # Optional: specify text color
                'insert': text_location,  # X, Y coordinates
            }
        )

        text_content = "Structure :"
        text_location = (6 * wall_thickness + xorigin, width - 26.5 * overall_depth)

        msp.add_text(
            text_content,
            dxfattribs={
                'height': wall_thickness / 4,  # Text height
                'layer': 'TEXT',  # Optional: specify a layer for the text
                'color': 7,  # Optional: specify text color
                'insert': text_location,  # X, Y coordinates
            }
        )

        text_content = "Designed :"
        text_location = (15.1 * wall_thickness + xorigin, width - 23 * overall_depth)

        msp.add_text(
            text_content,
            dxfattribs={
                'height': wall_thickness / 4,  # Text height
                'layer': 'TEXT',  # Optional: specify a layer for the text
                'color': 5,  # Optional: specify text color
                'insert': text_location,  # X, Y coordinates
            }
        )

        text_content = "Checked :"
        text_location = (15.1 * wall_thickness + xorigin, width - 25.5 * overall_depth)

        msp.add_text(
            text_content,
            dxfattribs={
                'height': wall_thickness / 4,  # Text height
                'layer': 'TEXT',  # Optional: specify a layer for the text
                'color': 3,  # Optional: specify text color
                'insert': text_location,  # X, Y coordinates
            }
        )
        today = datetime.today().strftime('%Y-%m-%d')
        text_content = f"Date: {today} "
        text_location = (15.1 * wall_thickness + xorigin, width - 21.5 * overall_depth)

        msp.add_text(
            text_content,
            dxfattribs={
                'height': wall_thickness / 6,  # Text height
                'layer': 'TEXT',  # Optional: specify a layer for the text
                'color': 21,  # Optional: specify text color
                'insert': text_location,  # X, Y coordinates
            }
        )


        dim.render()
        file = "Fixed.dxf"
        doc.saveas(file)
        print("Drwaing is created for Fixed beam as:", file)
        # Save the document as a DXF file
        filename = f'FixedBeam_{o_d}x{round(wall_thickness * 100, 1)}.dxf'
        filepath = os.path.join('generated_files', filename)
        os.makedirs('generated_files', exist_ok=True)
        doc.saveas(filepath)
        return send_file(filepath, as_attachment=True, download_name=filename)
    # Save the DXF file
    if (beam_type == "Cantilever"):
        filename = f'Cantilever_{provided_depth}x{round(wall_thickness * 100, 1)}.dxf'
        filepath = os.path.join('generated_files', filename)
        os.makedirs('generated_files', exist_ok=True)
        doc.saveas(filepath)
        return send_file(filepath, as_attachment=True, download_name=filename)


if __name__ == '__main__':
    app.run(debug=True)
