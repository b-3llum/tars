import UIKit

@main
class AppDelegate: UIResponder, UIApplicationDelegate {

    var window: UIWindow?

    func application(_ application: UIApplication,
                     didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]?) -> Bool {

        window = UIWindow(frame: UIScreen.main.bounds)
        let chat = ChatViewController()
        let nav = UINavigationController(rootViewController: chat)
        nav.navigationBar.prefersLargeTitles = false
        window?.rootViewController = nav
        window?.makeKeyAndVisible()

        return true
    }
}
