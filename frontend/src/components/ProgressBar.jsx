import React from 'react';
import { motion } from 'framer-motion';

const ProgressBar = ({ stage, percent, current, total }) => {
  return (
    <div className="w-full mt-4">
      <div className="flex justify-between text-xs mb-1">
        <span className="text-textPrimary font-medium">{stage}</span>
        {total > 0 && (
          <span className="text-textMuted font-mono">
            {current} / {total} chunks
          </span>
        )}
      </div>
      <div className="h-2 w-full bg-borderBase rounded-full overflow-hidden">
        <motion.div 
          className="h-full bg-gradient-to-r from-accentTeal to-[#0ea5e9]"
          initial={{ width: 0 }}
          animate={{ width: `${percent}%` }}
          transition={{ duration: 0.5, ease: "easeOut" }}
        />
      </div>
    </div>
  );
};

export default ProgressBar;
