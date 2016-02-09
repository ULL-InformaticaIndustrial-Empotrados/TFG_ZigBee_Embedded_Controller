/*
 * Copyright © 2016 Canonical Ltd.
 *
 * This program is free software: you can redistribute it and/or modify it
 * under the terms of the GNU General Public License version 3,
 * as published by the Free Software Foundation.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 *
 * Authored by: Cemil Azizoglu <cemil.azizoglu@canonical.com>
 *              Alan Griffiths <alan@octopull.co.uk>
 */

#include "mir_server_fullscreen_wm.h"
#include "mir_server_basic_window_manager.h"

#include "mir/server.h"
#include "mir/scene/session.h"
#include "mir/scene/surface_creation_parameters.h"
#include "mir/shell/display_layout.h"

namespace msn = mir::snappy;
namespace mf = mir::frontend;
namespace ms = mir::scene;
namespace msh = mir::shell;
using namespace mir::geometry;

namespace
{

class FullscreenWindowManagerPolicy  : public msn::WindowManagementPolicy
{
public:
    FullscreenWindowManagerPolicy(msn::WindowManagerTools* const /*tools*/, std::shared_ptr<msh::DisplayLayout> const& display_layout) :
        display_layout{display_layout} {}

    void handle_session_info_updated(SessionInfoMap& /*session_info*/, Rectangles const& /*displays*/) {}

    void handle_displays_updated(SessionInfoMap& /*session_info*/, Rectangles const& /*displays*/) {}

    auto handle_place_new_surface(
        std::shared_ptr<ms::Session> const& /*session*/,
        ms::SurfaceCreationParameters const& request_parameters)
    -> ms::SurfaceCreationParameters
    {
        auto placed_parameters = request_parameters;

        Rectangle rect{request_parameters.top_left, request_parameters.size};
        display_layout->size_to_output(rect);
        placed_parameters.size = rect.size;

        return placed_parameters;
    }
    void handle_modify_surface(
        std::shared_ptr<ms::Session> const& /*session*/,
        std::shared_ptr<ms::Surface> const& /*surface*/,
        msh::SurfaceSpecification const& /*modifications*/)
    {
    }

    void handle_new_surface(std::shared_ptr<ms::Session> const& /*session*/, std::shared_ptr<ms::Surface> const& /*surface*/)
    {
    }

    void handle_delete_surface(std::shared_ptr<ms::Session> const& session, std::weak_ptr<ms::Surface> const& surface)
        { session->destroy_surface(surface); }

    int handle_set_state(std::shared_ptr<ms::Surface> const& /*surface*/, MirSurfaceState value)
        { return value; }

    bool handle_keyboard_event(MirKeyboardEvent const* /*event*/) { return false; }

    bool handle_touch_event(MirTouchEvent const* /*event*/) { return false; }

    bool handle_pointer_event(MirPointerEvent const* /*event*/) { return false; }

    void handle_raise_surface(
        std::shared_ptr<ms::Session> const& /*session*/,
        std::shared_ptr<ms::Surface> const& /*surface*/)
    {
    }

    void generate_decorations_for(
        std::shared_ptr<ms::Session> const&,
        std::shared_ptr<ms::Surface> const&,
        SurfaceInfoMap&,
        std::function<mf::SurfaceId(std::shared_ptr<ms::Session> const&, ms::SurfaceCreationParameters const&)> const&)
    {
    }
private:
    std::shared_ptr<msh::DisplayLayout> const display_layout;
};

}

using FullscreenWindowManager = msn::WindowManagerBuilder<FullscreenWindowManagerPolicy>;

void msn::use_full_screen_window_manager(Server& server)
{
    server.override_the_window_manager_builder([&server](msh::FocusController* focus_controller)
        -> std::shared_ptr<msh::WindowManager>
        {
            return std::make_shared<FullscreenWindowManager>(focus_controller, server.the_shell_display_layout());
        });
}
