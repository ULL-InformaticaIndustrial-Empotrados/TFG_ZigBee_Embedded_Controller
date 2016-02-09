/*
 * Copyright © 2016 Canonical Ltd.
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License version 3 as
 * published by the Free Software Foundation.
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
 */

#include "mir_server_fullscreen_wm.h"

#include "mir/server.h"
#include "mir/report_exception.h"

#include <cstdlib>
#include <iostream>

namespace msn = mir::snappy;

int main(int argc, char const* argv[])
try
{
    std::cout << "Mir server snap started" << std::endl;
    mir::Server server;

    msn::use_full_screen_window_manager(server);

    server.set_command_line(argc, argv);
    server.apply_settings();
    server.run();

    std::cout << "Mir server snap ended" << std::endl;
    return server.exited_normally() ? EXIT_SUCCESS : EXIT_FAILURE;
}
catch (...)
{
    mir::report_exception();
    return EXIT_FAILURE;
}
