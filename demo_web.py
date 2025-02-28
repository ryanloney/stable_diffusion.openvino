# -- coding: utf-8 --`
import argparse
import os
import random
import streamlit as st
from streamlit_drawable_canvas import st_canvas
import numpy as np
import cv2
from  PIL import Image, ImageEnhance
import numpy as np
# engine
from stable_diffusion_engine import StableDiffusionEngine
# scheduler
from diffusers import PNDMScheduler


def run(engine):
    def clear_output():
        if os.path.isfile('output.png'):
            os.remove('output.png')

    # init session_state if needed
    if 'random_seed' not in st.session_state:
        st.session_state.random_seed = random.randint(0, 2 ** 31)
    if 'seed' not in st.session_state:
        st.session_state.seed = st.session_state.random_seed
    if 'clicked_generate' not in st.session_state:
        st.session_state.clicked_generate = False
    if 'cleared_output' not in st.session_state:
        clear_output()
        st.session_state.cleared_output = True

    with st.form(key="request"):
        with st.sidebar:
            prompt = st.text_area(label='Enter prompt')

            # if we are generating and the seed is random, generate a new random seed
            if prompt and st.session_state.clicked_generate and st.session_state.seed == st.session_state.random_seed:
                st.session_state.random_seed = random.randint(0, 2 ** 31)
                st.session_state.seed = st.session_state.random_seed

            with st.expander("Initial image"):
                init_image = st.file_uploader("init_image", type=['jpg','png','jpeg'])

                stroke_width = st.slider("stroke_width", 1, 100, 50)

                stroke_color = st.color_picker("stroke_color", "#00FF00")

                canvas_result = st_canvas(
                    fill_color="rgb(0, 0, 0)",
                    stroke_width = stroke_width,
                    stroke_color = stroke_color,
                    background_color = "#000000",
                    background_image = Image.open(init_image) if init_image else None,
                    height = 478,
                    width = 478,
                    drawing_mode = "freedraw",
                    key = "canvas"
                )

                strength = st.slider(
                    label='strength',
                    min_value = 0.0,
                    max_value = 1.0,
                    value = 0.5
                )

            if init_image is not None:
                init_image = cv2.cvtColor(np.array(Image.open(init_image)), cv2.COLOR_RGB2BGR)

            if canvas_result.image_data is not None:
                mask = cv2.cvtColor(canvas_result.image_data, cv2.COLOR_BGRA2GRAY)
                mask[mask > 0] = 255

                # ignore empty mask
                if not mask.any():
                    mask = None
            else:
                mask = None

            num_inference_steps = st.select_slider(
                label='num_inference_steps',
                options=range(1, 150),
                value=32
            )

            guidance_scale = st.select_slider(
                label='guidance_scale',
                options=range(1, 21),
                value=7
            )

            seed = st.number_input(
                label='seed',
                key='seed',
                min_value = 0,
                max_value = 2 ** 31
            )

            def clicked_generate():
                st.session_state.clicked_generate = True

            generate = st.form_submit_button(
                label = 'Generate',
                on_click = clicked_generate
            )

        image_container = st.empty()

        def update_image(image, i = None):
            cv2.imwrite('output.png', image)
            image = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
            image_container.image(image, width=512, caption=None if i is None else f'{i + 1} / {num_inference_steps}')

        if prompt and st.session_state.clicked_generate:
            st.session_state.clicked_generate = False

            clear_output()
            np.random.seed(seed)
            image = engine(
                prompt = prompt,
                init_image = init_image,
                mask = mask,
                strength = strength,
                num_inference_steps = num_inference_steps,
                guidance_scale = guidance_scale
            )
            update_image(image)
        elif os.path.isfile('output.png'):
            update_image(cv2.imread('output.png'))

@st.cache(allow_output_mutation=True)
def load_engine(args):
    scheduler = PNDMScheduler(
        beta_start=args.beta_start,
        beta_end=args.beta_end,
        beta_schedule=args.beta_schedule,
        skip_prk_steps = True,
        tensor_format="np"
    )
    engine = StableDiffusionEngine(
        model = args.model,
        scheduler = scheduler,
        tokenizer = args.tokenizer
    )
    return engine


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    # pipeline configure
    parser.add_argument("--model", type=str, default="bes-dev/stable-diffusion-v1-4-openvino", help="model name")
    # scheduler params
    parser.add_argument("--beta-start", type=float, default=0.00085, help="LMSDiscreteScheduler::beta_start")
    parser.add_argument("--beta-end", type=float, default=0.012, help="LMSDiscreteScheduler::beta_end")
    parser.add_argument("--beta-schedule", type=str, default="scaled_linear", help="LMSDiscreteScheduler::beta_schedule")
    # tokenizer
    parser.add_argument("--tokenizer", type=str, default="openai/clip-vit-large-patch14", help="tokenizer")

    try:
        args = parser.parse_args()
    except SystemExit as e:
        # This exception will be raised if --help or invalid command line arguments
        # are used. Currently streamlit prevents the program from exiting normally
        # so we have to do a hard exit.
        os._exit(e.code)

    engine = load_engine(args)
    run(engine)
