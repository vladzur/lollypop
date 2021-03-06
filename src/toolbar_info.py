# Copyright (c) 2014-2016 Cedric Bellegarde <cedric.bellegarde@adishatz.org>
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

from gi.repository import Gtk, Gdk, GLib
from cgi import escape

from lollypop.pop_menu import TrackMenuPopover
from lollypop.pop_tunein import TuneinPopover
from lollypop.pop_externals import ExternalsPopover
from lollypop.pop_info import InfoPopover
from lollypop.pop_menu import PopToolbarMenu
from lollypop.controllers import InfosController
from lollypop.define import Lp, Type, ArtSize


class ToolbarInfo(Gtk.Bin, InfosController):
    """
        Informations toolbar
    """

    def __init__(self):
        """
            Init toolbar
        """
        Gtk.Bin.__init__(self)
        InfosController.__init__(self, ArtSize.SMALL)
        builder = Gtk.Builder()
        builder.add_from_resource('/org/gnome/Lollypop/ToolbarInfo.ui')
        builder.connect_signals(self)
        self.__pop_tunein = None
        self.__pop_info = None
        self.__timeout_id = None
        self.__width = 0

        self._infobox = builder.get_object('info')
        self.add(self._infobox)

        self._spinner = builder.get_object('spinner')

        self.__labels = builder.get_object('nowplaying_labels')
        self.__labels.connect('query-tooltip', self.__on_query_tooltip)
        self.__labels.set_property('has-tooltip', True)

        self._title_label = builder.get_object('title')
        self._artist_label = builder.get_object('artist')
        self._cover = builder.get_object('cover')
        self._cover.set_property('has-tooltip', True)
        # Since GTK 3.20, we can set cover full height
        if Gtk.get_minor_version() > 18:
            self._cover.get_style_context().add_class('toolbar-cover-frame')
        else:
            self._cover.get_style_context().add_class('small-cover-frame')

        self.connect('realize', self.__on_realize)
        Lp().player.connect('loading-changed', self.__on_loading_changed)
        Lp().art.connect('album-artwork-changed', self.__update_cover)
        Lp().art.connect('radio-artwork-changed', self.__update_logo)

    def do_get_preferred_width(self):
        """
            We force preferred width
            @return (int, int)
        """
        return (self.__width, self.__width)

    def get_preferred_height(self):
        """
            Return preferred height
            @return (int, int)
        """
        return self.__labels.get_preferred_height()

    def set_width(self, width):
        """
            Set widget width
            @param width as int
        """
        self.__width = width
        self.set_property('width-request', width)

#######################
# PROTECTED           #
#######################
    def _on_title_press_event(self, widget, event):
        """
            On long press: show current track menu
            @param widget as Gtk.Widget
            @param event as Gdk.Event

        """
        self.__timeout_id = GLib.timeout_add(500, self.__show_track_menu)
        return True

    def _on_title_release_event(self, widget, event):
        """
            Show track information popover
            On long press/right click: show current track menu
            @param widget as Gtk.Widget
            @param event as Gdk.Event
        """
        if self.__timeout_id is not None:
            GLib.source_remove(self.__timeout_id)
            self.__timeout_id = None
            if Lp().player.current_track.id == Type.EXTERNALS:
                expopover = ExternalsPopover()
                expopover.set_relative_to(widget)
                expopover.populate()
                expopover.show()
            elif Lp().player.current_track.id is not None:
                if event.button == 1:
                    if Lp().player.current_track.id == Type.RADIOS:
                        if self.__pop_tunein is None:
                            self.__pop_tunein = TuneinPopover()
                            self.__pop_tunein.populate()
                            self.__pop_tunein.set_relative_to(widget)
                        self.__pop_tunein.show()
                    else:
                        if self.__pop_info is None:
                            self.__pop_info = InfoPopover()
                            self.__pop_info.set_relative_to(widget)
                        self.__pop_info.show()
                else:
                    self.__show_track_menu()
        return True

    def _on_eventbox_realize(self, eventbox):
        """
            Show hand cursor over
        """
        eventbox.get_window().set_cursor(Gdk.Cursor(Gdk.CursorType.HAND1))

#######################
# PRIVATE             #
#######################
    def __update_cover(self, art, album_id):
        """
            Update cover for album_id
            @param art as Art
            @param album id as int
        """
        if Lp().player.current_track.album.id == album_id:
            surface = Lp().art.get_album_artwork(
                                       Lp().player.current_track.album,
                                       self._artsize,
                                       self._cover.get_scale_factor())
            self._cover.set_from_surface(surface)
            del surface

    def __update_logo(self, art, name):
        """
            Update logo for name
            @param art as Art
            @param name as str
        """
        if Lp().player.current_track.album_artist == name:
            pixbuf = Lp().art.get_radio_artwork(name, self._artsize)
            self._cover.set_from_surface(pixbuf)
            del pixbuf

    def __show_track_menu(self):
        """
            Show current track menu
        """
        self.__timeout_id = None
        if Lp().player.current_track.id >= 0:
            popover = TrackMenuPopover(
                        Lp().player.current_track,
                        PopToolbarMenu(Lp().player.current_track.id))
            popover.set_relative_to(self._infobox)
            popover.show()

    def __on_loading_changed(self, player):
        """
            Show spinner based on loading status
            @param player as player
        """
        self._title_label.hide()
        self._artist_label.hide()
        self._cover.hide()
        self._spinner.show()
        self._spinner.start()
        self._infobox.show()

    def __on_realize(self, toolbar):
        """
            Calculate art size
            @param toolbar as ToolbarInfos
        """
        style = self.get_style_context()
        padding = style.get_padding(style.get_state())
        self._artsize = self.get_allocated_height()\
            - padding.top - padding.bottom
        # Since GTK 3.20, we can set cover full height
        if Gtk.get_minor_version() < 20:
            self._artsize -= 2

    def __on_query_tooltip(self, widget, x, y, keyboard, tooltip):
        """
            Show tooltip if needed
            @param widget as Gtk.Widget
            @param x as int
            @param y as int
            @param keyboard as bool
            @param tooltip as Gtk.Tooltip
        """
        # Can't add a \n in markup
        # GTK bug => https://bugzilla.gnome.org/show_bug.cgi?id=749965
        layout_title = self._title_label.get_layout()
        layout_artist = self._artist_label.get_layout()
        if layout_title.is_ellipsized() or layout_artist.is_ellipsized():
            artist = escape(self._artist_label.get_text())
            title = escape(self._title_label.get_text())
            tooltip.set_markup("<b>%s</b> - %s" % (artist, title))
        else:
            return False
        return True
