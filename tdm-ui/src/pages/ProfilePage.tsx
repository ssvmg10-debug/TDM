import { motion } from "framer-motion";
import { User, Mail, Building2, Calendar } from "lucide-react";

const container = { hidden: { opacity: 0 }, show: { opacity: 1, transition: { staggerChildren: 0.06 } } };
const item = { hidden: { opacity: 0, y: 12 }, show: { opacity: 1, y: 0, transition: { duration: 0.4 } } };

const ProfilePage = () => {
  const profile = {
    name: "Test User",
    email: "test@fusiondatax.io",
    role: "Platform Admin",
    memberSince: "2024-01-15",
  };

  return (
    <motion.div variants={container} initial="hidden" animate="show" className="space-y-6 max-w-[800px] mx-auto">
      <motion.div variants={item}>
        <h1 className="text-2xl font-display font-bold text-foreground">Profile</h1>
        <p className="text-sm text-muted-foreground mt-1">Your account information</p>
      </motion.div>

      <motion.div variants={item} className="glass-card p-6">
        <div className="flex items-center gap-6 mb-6">
          <div className="w-20 h-20 rounded-full bg-primary/20 flex items-center justify-center text-2xl font-bold text-primary">
            TF
          </div>
          <div>
            <h2 className="text-xl font-semibold text-foreground">{profile.name}</h2>
            <p className="text-sm text-muted-foreground">{profile.role}</p>
          </div>
        </div>
        <div className="space-y-4">
          <div className="flex items-center gap-3 p-3 rounded-lg bg-muted/20">
            <Mail className="w-4 h-4 text-muted-foreground" />
            <div>
              <p className="text-xs text-muted-foreground">Email</p>
              <p className="text-sm font-medium text-foreground">{profile.email}</p>
            </div>
          </div>
          <div className="flex items-center gap-3 p-3 rounded-lg bg-muted/20">
            <Building2 className="w-4 h-4 text-muted-foreground" />
            <div>
              <p className="text-xs text-muted-foreground">Role</p>
              <p className="text-sm font-medium text-foreground">{profile.role}</p>
            </div>
          </div>
          <div className="flex items-center gap-3 p-3 rounded-lg bg-muted/20">
            <Calendar className="w-4 h-4 text-muted-foreground" />
            <div>
              <p className="text-xs text-muted-foreground">Member since</p>
              <p className="text-sm font-medium text-foreground">{profile.memberSince}</p>
            </div>
          </div>
        </div>
      </motion.div>
    </motion.div>
  );
};

export default ProfilePage;
