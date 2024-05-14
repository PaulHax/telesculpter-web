from .assets import ASSETS
from trame.widgets import quasar, html


class VideoControls(html.Div):
    def __init__(
        self,
        current_frame="video_current_frame",
        n_frames="video_n_frames",
        play_status="video_playing",
        play_speed="video_play_speed",
        play_speed_label="video_play_speed_label",
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
                classes="col-8 no-transition",
                v_model=(current_frame, 1),
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
                v_model_number=(current_frame, 1),
                outlined=True,
                type="number",
                dense=True,
                style="min-width:3.75rem",
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
                style="min-width:6.25rem",
                v_model=(play_speed, 60),
                min=(-20,),
                max=(60,),
                step=(1,),
                markers=True,
                snap=True,
                track_size="25px",
                thumb_size="5px",
            )
            # enable once the reported fps matches the actual performance
            # html.Div(
            #    f"{{{{ {play_speed_label} }}}}",
            #    classes="text-right",
            #    style="width: 50px;",
            # )


class FileMenu(html.Div):
    def __init__(
        self,
        on_menu_file_open,
        on_menu_file_export_meta,
        on_menu_file_export_klv,
        on_menu_file_remove_burnin,
        on_menu_file_cancel,
        on_menu_file_quit,
        **kwargs,
    ):
        super().__init__("File", classes="cursor-pointer non-selectable")
        close_popup = dict(raw_attrs=["v-close-popup"])
        with self:
            with quasar.QMenu():
                with quasar.QList(dense=True, style="min-width: 200px"):
                    with quasar.QItem(
                        clickable=True,
                        click=on_menu_file_open,
                        **close_popup,
                    ):
                        with quasar.QItemSection(style="max-width: 20px;"):
                            quasar.QIcon(name="folder", size="xs")
                        quasar.QItemSection(
                            "Open Video...", classes="cursor-pointer non-selectable"
                        )
                    quasar.QSeparator()
                    with quasar.QItem(clickable=True):
                        with quasar.QItemSection(style="max-width: 20px;"):
                            # quasar.QIcon(name="description", size="xs")
                            pass
                        quasar.QItemSection(
                            "Export", classes="cursor-pointer non-selectable"
                        )
                        with quasar.QItemSection(side=True):
                            quasar.QIcon(name="keyboard_arrow_right")
                        with quasar.QMenu(
                            anchor="top end", raw_attrs=['self="top start"']
                        ):
                            with quasar.QList(dense=True, style="min-width: 100px"):
                                with quasar.QItem(
                                    clickable=True,
                                    **close_popup,
                                    click=on_menu_file_export_meta,
                                ):
                                    quasar.QItemSection(
                                        "Metadata...",
                                        classes="cursor-pointer non-selectable",
                                    )
                                with quasar.QItem(
                                    clickable=True,
                                    **close_popup,
                                    click=on_menu_file_export_klv,
                                ):
                                    quasar.QItemSection(
                                        "KLV Packets...",
                                        classes="cursor-pointer non-selectable",
                                    )
                    with quasar.QItem(
                        clickable=True,
                        **close_popup,
                        click=on_menu_file_remove_burnin,
                        disable=True,
                    ):
                        with quasar.QItemSection(style="max-width: 20px;"):
                            # quasar.QIcon(name="description", size="xs")
                            pass
                        quasar.QItemSection(
                            "Remove Burn-in...", classes="cursor-pointer non-selectable"
                        )
                    quasar.QSeparator()
                    with quasar.QItem(
                        clickable=True,
                        **close_popup,
                        click=on_menu_file_cancel,
                    ):
                        with quasar.QItemSection(style="max-width: 20px;"):
                            quasar.QIcon(name="do_not_disturb_alt", size="xs")
                        quasar.QItemSection(
                            "Cancel", classes="cursor-pointer non-selectable"
                        )
                    quasar.QSeparator()
                    with quasar.QItem(
                        clickable=True,
                        **close_popup,
                        click=on_menu_file_quit,
                    ):
                        with quasar.QItemSection(style="max-width: 20px;"):
                            quasar.QIcon(name="power_settings_new", size="xs")
                        quasar.QItemSection(
                            "Quit", classes="cursor-pointer non-selectable"
                        )


class ViewMenu(html.Div):
    def __init__(
        self,
        on_menu_view_play,
        on_menu_view_loop,
        on_menu_view_reset,
        on_menu_view_toggle_meta,
        on_menu_view_toggle_log,
        **kwargs,
    ):
        super().__init__("View", classes="cursor-pointer non-selectable")
        close_popup = dict(raw_attrs=["v-close-popup"])
        with self:
            with quasar.QMenu():
                with quasar.QList(dense=True, style="min-width: 200px"):
                    with quasar.QItem(
                        clickable=True,
                        click=on_menu_view_play,
                        **close_popup,
                    ):
                        with quasar.QItemSection(style="max-width: 20px;"):
                            quasar.QIcon(name="play_arrow", size="xs")
                        quasar.QItemSection(
                            "Play Slideshow", classes="cursor-pointer non-selectable"
                        )

                    with quasar.QItem(
                        clickable=True,
                        click=on_menu_view_loop,
                        **close_popup,
                    ):
                        with quasar.QItemSection(style="max-width: 20px;"):
                            quasar.QIcon(name="repeat", size="xs")
                        quasar.QItemSection(
                            "Loop Slideshow", classes="cursor-pointer non-selectable"
                        )
                    quasar.QSeparator()
                    with quasar.QItem(
                        clickable=True,
                        click=on_menu_view_reset,
                        disable=True,
                        **close_popup,
                    ):
                        with quasar.QItemSection(style="max-width: 20px;"):
                            quasar.QIcon(name="crop_free", size="xs")
                        quasar.QItemSection(
                            "Reset View", classes="cursor-pointer non-selectable"
                        )
                    quasar.QSeparator()
                    with quasar.QItem(
                        clickable=True,
                        click=on_menu_view_reset,
                        disable=True,
                        **close_popup,
                    ):
                        with quasar.QItemSection(style="max-width: 20px;"):
                            quasar.QIcon(name="palette", size="xs")
                        quasar.QItemSection(
                            "Background Color...",
                            classes="cursor-pointer non-selectable",
                        )
                    quasar.QSeparator()
                    with quasar.QItem(
                        clickable=True,
                        click=on_menu_view_toggle_meta,
                    ):
                        with quasar.QItemSection(style="max-width: 20px;"):
                            quasar.QIcon(
                                name=(
                                    "show_view_metadata ? 'visibility' : 'visibility_off'",
                                ),
                                size="xs",
                            )
                        quasar.QItemSection(
                            "Metadata", classes="cursor-pointer non-selectable"
                        )
                    with quasar.QItem(
                        clickable=True,
                        click=on_menu_view_toggle_log,
                    ):
                        with quasar.QItemSection(style="max-width: 20px;"):
                            quasar.QIcon(
                                name=(
                                    "show_view_log ? 'visibility' : 'visibility_off'",
                                ),
                                size="xs",
                            )
                        quasar.QItemSection(
                            "Log Viewer", classes="cursor-pointer non-selectable"
                        )


class HelpMenu(html.Div):
    def __init__(
        self,
        on_menu_help_manual,
        on_menu_help_about,
        **kwargs,
    ):
        super().__init__("Help", classes="cursor-pointer non-selectable")
        close_popup = dict(raw_attrs=["v-close-popup"])
        with self:
            with quasar.QMenu():
                with quasar.QList(dense=True, style="min-width: 200px"):
                    with quasar.QItem(
                        clickable=True,
                        click=on_menu_help_manual,
                        disable=True,
                        **close_popup,
                    ):
                        with quasar.QItemSection(style="max-width: 20px;"):
                            quasar.QIcon(name="question_mark", size="xs")
                        quasar.QItemSection(
                            "BurnOut User Manual",
                            classes="cursor-pointer non-selectable",
                        )
                    quasar.QSeparator()
                    with quasar.QItem(
                        clickable=True,
                        click=on_menu_help_about,
                        disable=True,
                        **close_popup,
                    ):
                        with quasar.QItemSection(style="max-width: 20px;"):
                            html.Img(src=ASSETS.favicon, style="height: 20px")
                        quasar.QItemSection(
                            "About BurnOut", classes="cursor-pointer non-selectable"
                        )
