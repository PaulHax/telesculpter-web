from trame.widgets import quasar, html


class VideoControls(html.Div):
    def __init__(
        self,
        current_frame="video_current_frame",
        n_frames="video_n_frames",
        play_status="video_playing",
        play_speed="video_play_speed",
        play_loop="video_play_loop",
        classes="",
        **kwargs,
    ):
        super().__init__(
            classes=f"row items-center q-gutter-sm full-width {classes}", **kwargs
        )

        self.server.state.setdefault(play_status, False)

        with self:
            quasar.QSlider(
                classes="col-8",
                v_model=(current_frame, 0),
                min=(1,),
                max=(n_frames, 1),
                step=(1,),
            )
            quasar.QToggle(
                v_model=(play_loop, True),
                checked_icon="repeat",
                unchecked_icon="skip_next",
                size="xl",
            )
            quasar.QInput(
                classes="col",
                v_model_number=(current_frame, 0),
                outlined=True,
                type="number",
                dense=True,
            )
            quasar.QSeparator(vertical=True)
            quasar.QBtn(
                size="sm",
                v_show=f"!{play_status}",
                round=True,
                icon="play_arrow",
                color="green",
                click=f"{play_status} = true",
            )
            quasar.QBtn(
                size="sm",
                v_show=f"{play_status}",
                round=True,
                icon="stop",
                color="red",
                click=f"{play_status} = false",
            )
            quasar.QSlider(
                classes="col",
                v_model=(play_speed, 1),
                min=(0.25,),
                max=(2,),
                step=(0.25,),
                markers=True,
                snap=True,
                track_size="25px",
                thumb_size="5px",
            )
            html.Div(
                f"x {{{{ {play_speed}.toFixed(2) }}}}",
                classes="text-right",
                style="width: 50px;",
            )
